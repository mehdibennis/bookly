## Documentation d'architecture — projet Bookly

Cette documentation donne une vue d'ensemble de l'architecture du projet, des couches logicielles, des composants clés, du flux de données, de l'environnement de développement local, du pipeline CI et des recommandations d'amélioration.

### 1) Résumé rapide

Bookly est une API web construite avec FastAPI, SQLAlchemy (async avec asyncpg), Redis (cache), Keycloak pour l'authentification, et des outils de monitoring (Prometheus, Grafana). Le projet suit des principes proches de la Clean Architecture : séparation nette entre Domain, Repositories, Services, API et Infrastructure.

Objectifs observables : code testable (pytest + pytest-asyncio), couverture élevée (~98% en CI), intégration continue (GitHub Actions), rapports de couverture (Codecov), et observabilité (Prometheus + Sentry intégrés).

### 2) Organisation en couches (fichiers / dossiers importants)

- `app/domain/` — entités et objets valeur (business rules). Doit rester framework-agnostique.
- `app/repositories/` — interfaces et implémentations des accès aux données (SQLAlchemy). Ex: `app/repositories/author_repository.py`, `book_repository.py`.
- `app/services/` — logique métier orchestrant repositories et autres services (ex: `author_service.py`, `book_service.py`).
- `app/schemas/` — Pydantic DTOs (API input/output).
- `app/api/` — routes FastAPI et mappers. Ex: `app/api/v1/routes/authors.py`, `books.py`.
- `app/db/session.py` — configuration SQLAlchemy async engine et `async_session` (actuellement créé à l'import depuis `Settings`).
- `app/core/` — middleware, error handlers, cache-service adapter. Ex: `cache_service.py`, `middleware.py`, `error_handlers.py`.
- `app/main.py` — point d'entrée FastAPI et montage des middlewares/routers.
- `tests/` — tests unitaires et d'intégration (pytest + pytest-asyncio). Fichiers: `tests/integration/*`, `tests/unit/*`.
- `conftest.py` (racine) et `tests/conftest.py` — fixtures partagées, logique de fallback pour environnements sans Postgres.
- `Dockerfile`, `docker-compose.yml` — services (Postgres, Redis, Keycloak, web, monitoring).
- `.github/workflows/ci.yml` — pipeline CI (unit/integration tests, coverage upload, post PR coverage comment).
- `Makefile` — commandes pratiques, cible utile : `make test-local` (lance pytest local pointant le conteneur Postgres mapé sur le port 15432).

### 3) Flux de données typique (requête -> DB)

1. Client HTTP appelle une route FastAPI (`app/api/v1/routes/...`).
2. La couche API convertit les payloads JSON en Pydantic schemas et appelle un Service.
3. Le Service encapsule la logique métier et appelle les Repositories pour les opérations persistantes.
4. Les Repositories utilisent SQLAlchemy async sessions (`app/db/session.py`) et retournent des entités/domain objects.
5. Le Service transforme/valide, puis renvoie au contrôleur qui sérialise la réponse via Pydantic.

Au besoin, la couche `app/core/cache_service.py` intercepte ou fournit une implémentation de cache (Noop/Redis) pour améliorer les performances.

### 4) Contrat minimal d'une couche Service (exemple)

- Entrées : Pydantic schema (dict / dataclass) ou valeurs primitives.
- Sorties : Domain entity ou DTO (Pydantic model) ou None.
- Erreurs : raise exceptions métier (domain-specific exceptions) converties en HTTP via `error_handlers`.
- Effets secondaires : appels aux repositories (CRUD) et éventuellement publication d'événements / cache invalidation.

Edge cases à considérer : entrées invalides, doublons (unique constraint), erreurs transitoires de DB (timeouts), concurrence (transactions), et absence de dépendances externes (Redis, Keycloak).

### 5) Tests et stratégie de test

- Les tests sont séparés en `tests/unit` et `tests/integration`.
- Les tests d'intégration s'attendent à une base Postgres et utilisent la configuration fournie dans `.env`.
- CI exécute la suite complète dans un conteneur avec un service Postgres. Les valeurs de `.env` indiquent :
  - `POSTGRES_USER=bookly_user`
  - `POSTGRES_PASSWORD=bookly_pass`
  - `POSTGRES_DB=bookly_db`
  - Le `docker-compose.yml` mappe le port Postgres local `15432` vers le port container `5432`.

- Pour le dev local : `make test-local` est fourni et exporte les env vars nécessaires (ou vous pouvez `export` manuellement). Exemple utilisé avec succès lors d'un run local :

```bash
POSTGRES_HOST=127.0.0.1 \
POSTGRES_PORT=15432 \
POSTGRES_USER=bookly_user \
POSTGRES_PASSWORD=bookly_pass \
POSTGRES_DB=bookly_db \
pytest -n 0 -q
```

Note: le projet attend désormais que les tests d'intégration utilisent la base Postgres fournie par `docker-compose` (mapping local 15432). Le fallback automatique vers SQLite a été retiré pour éviter une logique non fiable — si Postgres est inaccessible la suite de tests s'arrêtera avec un message expliquant comment démarrer les services localement (`docker compose up -d db redis`) ou utiliser `make test-local`.

### 6) CI / couverture / Codecov

- Le workflow GitHub Actions `ci.yml` instancie un service Postgres et exécute tests + upload vers Codecov. Un pas supplémentaire met à jour un commentaire unique sur la PR avec le pourcentage de couverture et la sunburst image.
- Objectif de couverture : >= 98% (CI actuel valide ~98.2%).

### 7) Observabilité et monitoring

- Prometheus : `docker-compose.yml` contient un service `prometheus` et `web` expose l'endpoint metrics si `ENABLE_METRICS=true`.
- Grafana/Loki/Promtail sont provisionnés pour visualiser métriques/logs.
- Sentry : DSN disponible via `.env`, et middleware Sentry activable via `ENABLE_SENTRY`.

### 8) Problèmes connus et décisions techniques

1. Import-time engine creation
   - `app/db/session.py` construit l'engine SQLAlchemy à l'import en lisant `Settings().DATABASE_URL`. Cela empêche de remplacer simplement `engine`/`async_session` à runtime dans `conftest` parce que d'autres modules peuvent avoir capturé la référence avant le swap.
   - Recommandation : refactoriser pour utiliser une factory lazy / function `get_engine()` et `get_async_session()` ou une DI (dépendance FastAPI) afin de pouvoir injecter/patcher l'engine en tests.

2. Fallback sqlite en local
   - Une solution temporaire existe dans `tests/conftest.py` / `conftest.py` pour détecter l'absence de Postgres et créer un sqlite temporaire. Limitation : ne couvre pas les modules qui ont déjà importé l'engine.
   - Option courte (rapide): rendre le fallback sqlite **inconditionnel** pour les runs `make test-local` (moins risqué et rapide). Option longue (robuste): refactor lazy-engine.

3. Auth / Keycloak
   - Certaines intégration tests se basent sur un Keycloak importé dans docker-compose. Localement, si Keycloak n'est pas disponible, il existe des mocks fixtures dans les tests.

### 9) Recommandations & prochaines étapes (priorisées)

Court terme (faible risque) :
- Ajouter une cible Makefile `make test-local` (déjà présente) et ajouter un `README` court indiquant les commandes à exécuter pour démarrer `docker compose up -d db redis` puis la commande de test local (exemples fournis ci-dessus).
- Ajouter un petit script shell `scripts/test-local.sh` qui exporte les vars depuis `.env` et lance pytest.

Long terme (robuste) :
- Refactor : rendre la création de l'engine SQLAlchemy lazy ou via une factory / dépendance injectée. Cela permettra :
  - swap propre en tests (sqlite ou test-engine),
  - meilleure isolation et contrôle de lifecycle (dispose/cleanup),
  - réduction du couplage et suppression des patches risqués dans `conftest`.

- Ajouter `codecov.yml` pour déléguer l'enforcement des seuils de couverture à Codecov (plutôt que parsing custom en CI).

Éventuels extras :
- Documenter la stratégie de fixtures (transaction rollback vs schema par worker) et expliquer l'utilisation de `PYTEST_XDIST_WORKER` si applicable.

### 10) Ressources et commandes utiles

- Démarrer les services utiles en local (docker-compose) :

```bash
docker compose up -d db redis keycloak
# attendre que Postgres soit up ; postgres sera exposé sur le port 15432 localement
```

- Lancer la suite de tests localement (rapide, sans docker exec) :

```bash
POSTGRES_HOST=127.0.0.1 \
POSTGRES_PORT=15432 \
POSTGRES_USER=bookly_user \
POSTGRES_PASSWORD=bookly_pass \
POSTGRES_DB=bookly_db \
pytest -n 0 -q
```

- Lancer tests dans le conteneur (comme CI) :

```bash
make test
```

# Architecture decisions (summary)

This project follows Clean Architecture / Onion (Ports & Adapters). Below are a couple of short, actionable rules to help contributors keep layers clean.

## Exceptions: domain vs core

- Domain exceptions live in `app/domain/exceptions.py`.
  - Purpose: represent pure business/domain errors (e.g. `NotFoundException`, `ConflictException`, `DomainException`).
  - Must not depend on HTTP, FastAPI, or status codes. They are raised by services and repositories.

- Application / HTTP exceptions live in `app/core/exceptions.py`.
  - Purpose: exceptions that carry HTTP semantics (status_code, user-facing messages) and are used by the API layer and tests that assert on status codes.
  - The API layer (in `app/core/error_handlers.py` and `app/main.py`) maps domain exceptions -> appropriate HTTP responses using these application exceptions or direct JSONResponses.

Rationale:
- Keeping domain errors framework-agnostic improves portability (CLI, background jobs, different web frameworks) and testability.
- The API layer is responsible for translating domain errors into transport-level errors (HTTP status codes + messages).

## Enforcement
- There's an architecture test at `tests/unit/test_architecture.py` which asserts that files under `app/domain/` do not import `app.core`, `app.api`, `app.db`, or other infra layers.
- If you need to add a new domain exception, add it to `app/domain/exceptions.py` and then update `app/core/error_handlers.py` if mapping to HTTP responses is required.

## Quick dev notes
- Services should raise domain exceptions from `app.domain.exceptions`.
- The API layer should catch/map domain exceptions to HTTP responses (handlers registered in `app/main.py`).
- `app/core/exceptions.py` remains the choice for HTTP-oriented exceptions used by the API and tests that assert `status_code`.
