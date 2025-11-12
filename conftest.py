"""Top-level conftest shim.

Some tests import helpers using `from conftest import ...` which fails when
`tests` is an importable package. Provide a small shim that re-exports the
real `tests.conftest` symbols so tests keep working without changing their
imports.

This file is intentionally minimal and only re-exports symbols from
`tests.conftest`.
"""

from importlib import import_module
from types import ModuleType

# Import the real tests.conftest module and re-export whatever it defines in
# its ``__all__``. This avoids using a ``from ... import *`` which ruff flags
# (F403), while still keeping existing test imports working.
_mod: ModuleType = import_module("tests.conftest")
_all = getattr(_mod, "__all__", [])

# If tests.conftest did not provide an explicit __all__, re-export all public
# attributes (names not starting with '_'). This covers fixtures/helpers like
# `get_auth_headers`, `get_rate_limit_headers`, etc., that tests import
# directly from the module.
if not _all:
    _all = [n for n in dir(_mod) if not n.startswith("_")]

for _name in _all:
    try:
        globals()[_name] = getattr(_mod, _name)
    except AttributeError:
        # Be resilient: if the symbol is missing, skip it.
        pass

__all__ = list(_all)
