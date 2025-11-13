DOCK_EXEC ?= docker compose exec

.PHONY: run build down test test-debug lint format migrate

PYTEST_ARGS ?=
ALEMBIC_ARGS ?= head
LINT_ARGS ?=

run:
	docker compose up -d
build:
	docker compose build
down:
	docker compose down
restart: down run
test:
	$(DOCK_EXEC) web bash -lc 'PYTHONPATH=/app pytest --cov --cov-report=term-missing --cov-report=html $(PYTEST_ARGS)'

# Run only unit tests (fast)
.PHONY: test-unit test-integration
test-unit:
	$(DOCK_EXEC) web bash -lc 'PYTHONPATH=/app pytest tests/unit -q $(PYTEST_ARGS)'

# Run only integration tests
test-integration:
	$(DOCK_EXEC) web bash -lc 'PYTHONPATH=/app pytest tests/integration -q $(PYTEST_ARGS)'

# Run tests in single-process mode for interactive debugging (no xdist).
# Use this when you want breakpoints or ipdb.set_trace() to stop execution.
# Example: make test-debug PYTEST_ARGS='tests/unit/my_test.py::test_something -q'
.PHONY: test-debug
test-debug:
	# Run pytest in single-process interactive mode for debugging.
	# Clear any addopts from pytest.ini (for example '-n auto') to avoid
	# passing duplicate/unknown -n options to pytest, then disable xdist.
	# Use an interactive exec (-it) so pytest/ipdb can read from the terminal when
	# running locally. We avoid changing $(DOCK_EXEC) global so CI isn't affected.
	docker compose exec -it web bash -lc 'PYTHONPATH=/app pytest -o addopts= -p no:xdist -s --maxfail=1 $(PYTEST_ARGS)'

test-local:
	# Run pytest locally (not in docker) for faster iteration when developing tests.
	# Clear any addopts from pytest.ini (for example '-n auto') to avoid
	# passing duplicate/unknown -n options to pytest, then disable xdist.
	# Use an interactive exec (-it) so pytest/ipdb can read from the terminal when
	POSTGRES_PORT=15432 POSTGRES_HOST=127.0.0.1 POSTGRES_USER=bookly_user POSTGRES_PASSWORD=bookly_pass POSTGRES_DB=bookly_db pytest -n 0 -q $(PYTEST_ARGS)

# ==============================
# logs
# ==============================
.PHONY: logs

logs:
	docker logs -f bookly-web-1

# ==============================
# Cleanup
# ==============================
.PHONY: sql-keycloak sql-bookly alembic-upgrade alembic-downgrade alembic-history alembic-current

sql-keycloak:
	$(DOCK_EXEC) db psql -U bookly_user -d keycloak_db

sql-bookly:
	$(DOCK_EXEC) db psql -U bookly_user -d bookly_db

alembic-upgrade:
	$(DOCK_EXEC) web alembic upgrade $(ALEMBIC_ARGS)

alembic-downgrade:
	$(DOCK_EXEC) web alembic downgrade $(ALEMBIC_ARGS)

alembic-history:
	$(DOCK_EXEC) web alembic history $(ALEMBIC_ARGS)

alembic-current:
	$(DOCK_EXEC) -T web alembic current

alembic-reset:
	$(DOCK_EXEC) -T web alembic stamp base
	$(DOCK_EXEC) -T web alembic upgrade head

# ==============================
# Cleanup
# ==============================
.PHONY: clean-py prune prune-volumes

clean-py:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
clean:
	$(MAKE) clean-py
	find . -type d -name 'htmlcov' -exec rm -rf {} +
	find . -type d -name '.mypy_cache' -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -exec rm -rf {} +
	find . -type d -name '.ruff_cache' -exec rm -rf {} +
	find . -type f -name 'app.log' -delete
	find . -type f -name '.coverage' -delete
	find . -type f -name '*.swp' -delete

prune:
	docker system prune -f

prune-volumes:
	docker volume prune -f


# ==============================
# Code quality and linters (local)
# ==============================
.PHONY: format lint mypy mypy-docker

format:
	isort .
	ruff format .
	ruff check . --fix

mypy:
	mypy .
mypy-docker:
	$(DOCK_EXEC) web mypy .

lint:
	ruff check . $(LINT_ARGS)
