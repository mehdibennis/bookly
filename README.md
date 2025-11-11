# Bookly - API de gestion de livres

> **API REST moderne** construite avec FastAPI, PostgreSQL, Redis et Keycloak

[![Tests](https://img.shields.io/badge/tests-129%20passing-success)]()
[![Coverage](https://img.shields.io/badge/coverage-99.78%25-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)]()

## 🚀 Démarrage rapide

```bash
# Cloner le dépôt
git clone <repo-url>
cd bookly

# Lancer tous les services (API, PostgreSQL, Redis, Keycloak)
docker compose up -d

# L'API est accessible sur http://localhost:8000
# Documentation interactive: http://localhost:8000/docs
```

## 📋 Prérequis

- Docker & Docker Compose
- Python 3.12+ (pour développement local)

## 🏗️ Architecture

```
bookly/
├── app/
│   ├── api/v1/routes/      # Endpoints API
│   ├── core/               # Config, auth, cache, error handlers
│   ├── db/                 # Models, session, migrations
│   ├── domain/             # Entities & interfaces (DDD)
│   ├── repositories/       # Couche accès données
│   ├── schemas/            # DTOs Pydantic
│   └── services/           # Logique métier
├── tests/                  # Suite de tests (129 tests)
├── docker-compose.yml
└── Dockerfile
```

**Patterns utilisés:**
- Domain-Driven Design (DDD)
- Repository Pattern
- Unit of Work
- Dependency Injection

## 🧪 Tests & Qualité

**Métriques:**
- **Coverage:** 99.78%
- **Tests:** 129 passants
- **Temps d'exécution:** ~60s (parallèle)

### Lancer les tests

```bash
# Tests en parallèle (recommandé)
docker compose run --rm web pytest

# Tests en série (debug)
docker compose run --rm web pytest -n0

# Avec rapport détaillé
docker compose run --rm web pytest -v
```

**Documentation complète:** Voir [TESTS_README.md](./TESTS_README.md)

## 🔑 Fonctionnalités

### API Endpoints

| Endpoint | Méthode | Auth | Description |
|----------|---------|------|-------------|
| `/api/v1/books/` | GET | ❌ | Liste paginée des livres |
| `/api/v1/books/{id}` | GET | ✅ | Détails d'un livre |
| `/api/v1/books/` | POST | ✅ | Créer un livre |
| `/api/v1/books/{id}` | PUT | ✅ | Modifier un livre |
| `/api/v1/books/{id}` | DELETE | ✅ | Supprimer un livre |

| `/ping` | GET | ❌ | Health check |
| `/docs` | GET | ❌ | Documentation OpenAPI |

### Fonctionnalités techniques

✅ **Authentification** : Keycloak OIDC  
✅ **Cache** : Redis pour les listes paginées  
✅ **Rate Limiting** : slowapi (IP-based)  
✅ **Validation** : Pydantic v2  
✅ **ORM** : SQLAlchemy 2.0 (async)  
✅ **Admin** : SQLAdmin (en cours)  
✅ **Logs** : Structurés avec UUID de requête  
✅ **Tests** : pytest-asyncio + pytest-xdist  

## 🛠️ Développement

### Variables d'environnement

Créer un fichier `.env` à la racine :

```bash
# Database
POSTGRES_USER=bookly_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=bookly_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Application
SECRET_KEY=your_secret_key_here
DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000

# Keycloak
KEYCLOAK_SERVER_URL=http://keycloak:8080
KEYCLOAK_REALM=bookly
KEYCLOAK_CLIENT_ID=bookly-client
KEYCLOAK_CLIENT_SECRET=your_client_secret

# Redis
REDIS_URL=redis://redis:6379/0
```

### Commandes utiles

```bash
# Rebuild l'image
docker compose build web

# Logs en temps réel
docker compose logs -f web

# Shell dans le conteneur
docker compose exec web bash

# Migrations (à venir avec Alembic)
docker compose run --rm web alembic upgrade head

# Créer une migration
docker compose run --rm web alembic revision --autogenerate -m "description"
```

## 📚 Documentation API

La documentation interactive est disponible à `/docs` (Swagger UI) et `/redoc` (ReDoc).

**Exemple de requête:**

```bash
# Créer un livre (nécessite token)
curl -X POST "http://localhost:8000/api/v1/books/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell"
  }'

# Lister les livres (public)
curl "http://localhost:8000/api/v1/books/?page=1&size=10"
```

## 🔒 Sécurité

- **Authentification** : JWT via Keycloak
- **Rate limiting** : Protection DDoS basique
- **Validation** : Pydantic stricte sur tous les endpoints
- **CORS** : Configuré (ajuster selon environnement)
- **SQL Injection** : Protection via SQLAlchemy ORM
- **Secrets** : Gérés via variables d'environnement

## 🚧 Roadmap

- [ ] Migration complète Alembic
- [ ] SQLAdmin sécurisé avec RBAC
- [ ] CI/CD avec GitHub Actions
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Rate limiting avancé (par utilisateur)
- [ ] Soft delete pour les livres
- [ ] Historique des modifications

## 📞 Support & Contribution

### Bugs & Features

Ouvrir une issue sur GitHub avec :
- Description détaillée
- Steps to reproduce (si bug)
- Logs pertinents

### Contribution

1. Fork le projet
2. Créer une branche (`git checkout -b feature/amazing-feature`)
3. Commit (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

**Standards:**
- Coverage ≥ 99%
- Tests passants (129/129)
- Black + isort pour formatting
- Type hints complets

## 📄 Licence

[À définir]

## 👥 Auteurs

[À compléter]

---

**Built with ❤️ using FastAPI**
