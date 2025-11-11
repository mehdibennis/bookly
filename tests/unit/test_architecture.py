"""Architecture tests: ensure domain layer has no infra/API dependencies.

This test scans all Python modules under `app/domain/` and fails if any of them
import `app.*` modules that are not part of the domain (i.e. imports like
`app.core`, `app.db`, `app.api`, `app.repositories`, `app.services`, etc.).

This prevents accidental leakage of infrastructure or framework code into the
domain layer and can be run in CI to catch regressions.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple


FORBIDDEN_PREFIX = "app."  # any import starting with app. is suspect
ALLOWED_DOMAIN_PREFIX = "app.domain"


def _find_domain_files() -> List[Path]:
    root = Path("app") / "domain"
    return [p for p in root.rglob("*.py") if p.is_file()]


def _scan_file_for_forbidden_imports(path: Path) -> List[Tuple[int, str]]:
    """Return list of (lineno, module) for forbidden imports in the file."""
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    violations: List[Tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name  # e.g. 'app.core.config'
                if name.startswith(FORBIDDEN_PREFIX) and not name.startswith(ALLOWED_DOMAIN_PREFIX):
                    violations.append((node.lineno, name))

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            # handle relative imports: skip when module is None or starts with '.'
            if module.startswith(FORBIDDEN_PREFIX) and not module.startswith(ALLOWED_DOMAIN_PREFIX):
                violations.append((node.lineno, module))

    return violations


def test_domain_layer_has_no_infra_imports() -> None:
    domain_files = _find_domain_files()
    all_violations: List[Tuple[Path, int, str]] = []

    for path in domain_files:
        violations = _scan_file_for_forbidden_imports(path)
        for lineno, module in violations:
            all_violations.append((path, lineno, module))

    if all_violations:
        msgs = [f"{p}:{ln} imports {m}" for p, ln, m in all_violations]
        raise AssertionError("Domain layer has forbidden imports:\n" + "\n".join(msgs))
