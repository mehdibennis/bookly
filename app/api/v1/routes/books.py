from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_book_service
from app.api.mappers import BookMapper, PaginationMapper
from app.core.keycloak_auth import get_current_user
from app.schemas.book_schema import Book, BookCreate, BookUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.book_service import BookService

router = APIRouter(prefix="/books", tags=["books"])


# --- READ ALL (PAGINATED: page/size) ---
@router.get(
    "/",
    response_model=PaginatedResponse[Book],
    name="books:list",
    summary="Liste paginée des livres",
    description="""
    Récupère la liste complète des livres avec pagination.

    **Paramètres de pagination :**
    - `page` : Numéro de la page (>=1)
    - `size` : Nombre d'éléments par page (1-100)

    **Exemple de réponse :**
    ```json
    {
      "data": [
        {"id": 1, "title": "1984", "author": "George Orwell"}
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
    response_description="Liste paginée de livres avec métadonnées de pagination",
)
async def list_books(
    page: int = Query(1, ge=1, description="Numéro de page (>=1)", example=1),
    size: int = Query(
        10, ge=1, le=100, description="Taille de page (1-100)", example=10
    ),
    book_service: BookService = Depends(get_book_service),
):
    """Récupère la liste paginée des livres (pagination page/size)."""
    pagination = PaginationMapper.params_from_query(page, size)
    # PaginationMapper returns a PaginationParams value object; pass its
    # primitive fields to the service which expects (page, size) ints.
    result = await book_service.list_books_by_page(pagination.page, pagination.size)
    return PaginationMapper.result_to_response(result, BookMapper.entities_to_dtos)


# --- READ ONE ---
@router.get(
    "/{book_id}",
    response_model=Book,
    name="books:get",
    summary="Récupérer un livre par ID",
    description="""
    Récupère les détails complets d'un livre spécifique.

    **Authentification requise :** Token JWT valide

    **Erreurs possibles :**
    - `401 Unauthorized` : Token manquant ou invalide
    - `404 Not Found` : Livre inexistant
    """,
    responses={
        404: {"description": "Livre non trouvé"},
        401: {"description": "Non authentifié"},
    },
)
async def get_book(
    book_id: int,
    book_service: BookService = Depends(get_book_service),
    user=Depends(get_current_user),
):
    """Récupère un livre par son ID."""
    book = await book_service.get_book(book_id)
    return BookMapper.entity_to_dto(book)


# --- CREATE ---
@router.post(
    "/",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
    name="books:create",
    summary="Créer un nouveau livre",
    description="""
    Crée un nouveau livre dans la collection.

    **Authentification requise :** Token JWT valide

    **Règles de validation :**
    - Le titre et l'auteur ne peuvent pas être vides
    - Le titre est normalisé (capitalisation automatique)
    - Les titres en double sont interdits

    **Erreurs possibles :**
    - `400 Bad Request` : Données invalides
    - `409 Conflict` : Livre avec ce titre existe déjà
    """,
    responses={
        201: {"description": "Livre créé avec succès"},
        400: {"description": "Données invalides"},
        409: {"description": "Conflit : livre existant"},
    },
)
async def create_book(
    book_in: BookCreate,
    book_service: BookService = Depends(get_book_service),
    user=Depends(get_current_user),
):
    """Crée un nouveau livre."""
    book_data = BookMapper.create_dto_to_domain(book_in)
    book = await book_service.create_book(book_data)
    return BookMapper.entity_to_dto(book)


# --- PARTIAL UPDATE (PATCH) ---
@router.patch(
    "/{book_id}",
    response_model=Book,
    name="books:patch",
    summary="Mettre à jour partiellement un livre",
    description="""
    Met à jour les informations d'un livre existant.

    **Authentification requise :** Token JWT valide

    **Mise à jour partielle :** Tous les champs sont optionnels.

    **Erreurs possibles :**
    - `404 Not Found` : Livre inexistant
    - `409 Conflict` : Titre en conflit avec un autre livre
    """,
    responses={
        200: {"description": "Livre mis à jour partiellement"},
        404: {"description": "Livre non trouvé"},
        409: {"description": "Conflit de titre"},
    },
)
async def patch_book(
    book_id: int,
    book_in: BookUpdate,
    book_service: BookService = Depends(get_book_service),
    user=Depends(get_current_user),
):
    """Met à jour partiellement un livre (PATCH semantics)."""
    book_data = BookMapper.update_dto_to_domain(book_in)
    book = await book_service.partial_update_book(book_id, book_data)
    return BookMapper.entity_to_dto(book)


# --- DELETE ---
@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="books:delete",
    summary="Supprimer un livre",
    description="""
    Supprime définitivement un livre de la collection.

    **Authentification requise :** Token JWT valide

    **Erreurs possibles :**
    - `404 Not Found` : Livre inexistant
    """,
    responses={
        204: {"description": "Livre supprimé avec succès"},
        404: {"description": "Livre non trouvé"},
    },
)
async def delete_book(
    book_id: int,
    book_service: BookService = Depends(get_book_service),
    user=Depends(get_current_user),
):
    """Supprime un livre."""
    await book_service.delete_book(book_id)
