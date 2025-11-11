from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_author_service
from app.api.mappers import AuthorMapper, PaginationMapper
from app.core.keycloak_auth import get_current_user
from app.db.session import get_session
from app.schemas.author_schema import Author, AuthorCreate, AuthorUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.author_service import AuthorService

router = APIRouter(prefix="/authors", tags=["authors"])


# --- READ ALL (PAGINATED: page/size) ---
@router.get(
    "/",
    response_model=PaginatedResponse[Author],
    name="authors:list",
    summary="Liste paginée des auteurs",
    description="""
    Récupère la liste complète des auteurs avec pagination.

    **Paramètres de pagination :**
    - `page` : Numéro de la page (>=1)
    - `size` : Nombre d'éléments par page (1-100)

    **Exemple de réponse :**
    ```json
    {
      "data": [
    {"id": 1, "first_name": "George", "last_name": "Orwell", "birth_date": "1903-06-25", \
        "death_date": "1950-01-21", "nationality": "British", "bio": "George Orwell was an English novelist, essayist, journalist and critic..."}
      ],
      "meta": {
        "total": 50,
        "page": 1,
        "size": 10,
        "count": 10,
        "last_page": 5,
        "next_page": 2,
        "previous_page": null
      }
    }
    ```

    **Note :** Cet endpoint est public (pas d'authentification requise).
    """,
    response_description="Liste paginée d'auteurs avec métadonnées de pagination",
)
async def list_authors(
    page: int = Query(1, ge=1, description="Numéro de page (>=1)", example=1),
    size: int = Query(
        10, ge=1, le=100, description="Taille de page (1-100)", example=10
    ),
    search: str | None = Query(None, description="Filtre texte sur prénom/nom (ILIKE)"),
    session: AsyncSession = Depends(get_session),
    service: AuthorService = Depends(get_author_service),
):
    """Récupère la liste paginée des auteurs (pagination page/size), avec filtre optionnel 'search'."""
    domain_result = await service.list_authors_by_page(page, size, search)
    # Convert domain PaginatedResult -> API PaginatedResponse using mapper
    return PaginationMapper.result_to_response(
        domain_result, AuthorMapper.entities_to_dtos
    )


# --- READ ONE ---
@router.get(
    "/{author_id}",
    response_model=Author,
    name="authors:get",
    summary="Récupérer un auteur par ID",
    description="""
    Récupère les détails complets d'un auteur spécifique.

    **Authentification requise :** Token JWT valide

    **Erreurs possibles :**
    - `401 Unauthorized` : Token manquant ou invalide
    - `404 Not Found` : Auteur inexistant
    """,
    responses={
        404: {"description": "Auteur non trouvé"},
        401: {"description": "Non authentifié"},
    },
)
async def get_author(
    author_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
    service: AuthorService = Depends(get_author_service),
):
    """Récupère un auteur par son ID."""
    author = await service.get_author(author_id)
    return Author.model_validate(author.__dict__)  # pragma: no cover


# --- CREATE ---
@router.post(
    "/",
    response_model=Author,
    status_code=status.HTTP_201_CREATED,
    name="authors:create",
    summary="Créer un nouvel auteur",
    description="""
    Crée un nouvel auteur dans la collection.

    **Authentification requise :** Token JWT valide

    **Règles de validation :**
    - Le prénom et le nom ne peuvent pas être vides
    - Les noms sont normalisés (capitalisation automatique)
    - Les doublons (même prénom + nom) sont interdits

    **Erreurs possibles :**
    - `400 Bad Request` : Données invalides
    - `409 Conflict` : Auteur avec ce nom existe déjà
    """,
    responses={
        400: {"description": "Données invalides"},
        409: {"description": "Conflit : auteur existant"},
    },
)
async def create_author(
    author_in: AuthorCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
    service: AuthorService = Depends(get_author_service),
):
    """Crée un nouvel auteur."""
    author_data = AuthorMapper.create_dto_to_domain(author_in)
    author = await service.create_author(author_data)
    return Author.model_validate(author.__dict__)  # pragma: no cover


# --- PARTIAL UPDATE ---
@router.patch(
    "/{author_id}",
    response_model=Author,
    name="authors:partial_update",
    summary="Mettre à jour partiellement un auteur (PATCH)",
    description="""
    Met à jour partiellement les informations d'un auteur existant.

    **Authentification requise :** Token JWT valide

    **Mise à jour partielle :** Tous les champs sont optionnels. Seuls les champs fournis seront mis à jour.

    **Exemple de requête :**
    ```json
    {
      "first_name": "George",
      "nationality": "British"
    }
    ```
    Les autres champs (last_name, birth_date, etc.) ne seront pas modifiés.

    - `401 Unauthorized` : Token manquant ou invalide
    - `404 Not Found` : Auteur inexistant
    - `409 Conflict` : Nom en conflit avec un autre auteur
    """,
    responses={
        200: {"description": "Auteur mis à jour avec succès"},
        401: {"description": "Non authentifié"},
        404: {"description": "Auteur non trouvé"},
        409: {"description": "Conflit de nom avec un autre auteur"},
    },
)
async def partial_update_author(
    author_id: int,
    author_in: AuthorUpdate,
    session: AsyncSession = Depends(get_session),
    service: AuthorService = Depends(get_author_service),
    user=Depends(get_current_user),
):
    author_data = AuthorMapper.update_dto_to_domain(author_in)
    author = await service.partial_update_author(author_id, author_data)
    return Author.model_validate(author.__dict__)  # pragma: no cover


# --- DELETE ---
@router.delete(
    "/{author_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="authors:delete",
    summary="Supprimer un auteur",
    description="""
    Supprime définitivement un auteur de la collection.

    **Authentification requise :** Token JWT valide

    **Erreurs possibles :**
    - `404 Not Found` : Auteur inexistant
    """,
    responses={
        204: {"description": "Auteur supprimé avec succès"},
        404: {"description": "Auteur non trouvé"},
    },
)
async def delete_author(
    author_id: int,
    service: AuthorService = Depends(get_author_service),
    user=Depends(get_current_user),
):
    await service.delete_author(author_id)
