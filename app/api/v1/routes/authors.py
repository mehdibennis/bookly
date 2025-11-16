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
    summary="Get a paginated list of authors",
    description="""
    Retrieves the complete list of authors with pagination.

    **Pagination parameters:**
    - `page` : Page number (>=1)
    - `size` : Number of items per page (1-100)

    **Example response:**
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

    **Note:** This endpoint is public (no authentication required).
    """,
    response_description="Paginated list of authors with pagination metadata",
    responses={
        200: {"description": "Authors retrieved successfully"},
    },
)
async def list_authors(
    page: int = Query(1, ge=1, description="Page number (>=1)", example=1),
    size: int = Query(10, ge=1, le=100, description="Page size (1-100)", example=10),
    search: str | None = Query(
        None, description="Text filter on first/last name (ILIKE)"
    ),
    session: AsyncSession = Depends(get_session),
    service: AuthorService = Depends(get_author_service),
):
    """Retrieve a paginated list of authors (pagination page/size), with optional 'search' filter."""
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
    summary="Get an author by ID",
    description="""
    Retrieves the full details of a specific author.

    **Authentication required:** Valid JWT token
    **Possible errors:**
    - `401 Unauthorized` : Missing or invalid token
    - `404 Not Found` : Author does not exist
    """,
    responses={
        404: {"description": "Author not found"},
        401: {"description": "Unauthorized"},
        200: {"description": "Author retrieved successfully"},
    },
)
async def get_author(
    author_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
    service: AuthorService = Depends(get_author_service),
):
    """Retrieve an author by their ID."""
    author = await service.get_author(author_id)
    return Author.model_validate(author.__dict__)  # pragma: no cover


# --- CREATE ---
@router.post(
    "/",
    response_model=Author,
    status_code=status.HTTP_201_CREATED,
    name="authors:create",
    summary="Create a new author",
    description="""
    Create a new author in the collection.

    **Authentication required:** Valid JWT token

    **Validation rules:**
    - First name and last name cannot be empty
    - Names are normalized (automatic capitalization)
    - Duplicates (same first name + last name) are not allowed

    **Possible errors:**
    - `400 Bad Request` : Invalid data
    - `409 Conflict` : Author with this name already exists
    """,
    responses={
        400: {"description": "Invalid data"},
        409: {"description": "Conflict: existing author"},
        401: {"description": "Unauthorized"},
        201: {"description": "Author created successfully"},
    },
)
async def create_author(
    author_in: AuthorCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
    service: AuthorService = Depends(get_author_service),
):
    """Create a new author."""
    author_data = AuthorMapper.create_dto_to_domain(author_in)
    author = await service.create_author(author_data)
    return Author.model_validate(author.__dict__)  # pragma: no cover


# --- PARTIAL UPDATE ---
@router.patch(
    "/{author_id}",
    response_model=Author,
    name="authors:update",
    summary="Partially update an author (PATCH)",
    description="""
    Partially updates the information of an existing author.

    **Authentication required:** Valid JWT token
    **Partial update:** All fields are optional. Only the provided fields will be updated.

    **Example request:**
    ```json
    {
      "first_name": "George",
      "nationality": "British"
    }
    ```
    Other fields (last_name, birth_date, etc.) will not be modified.

    - `401 Unauthorized` : Missing or invalid token
    - `404 Not Found` : Author does not exist
    - `409 Conflict` : Name conflicts with another author
    """,
    responses={
        200: {"description": "Author updated successfully"},
        401: {"description": "Unauthorized"},
        404: {"description": "Author not found"},
        409: {"description": "Name conflicts with another author"},
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
    summary="Delete an author",
    description="""
    Permanently deletes an author from the collection.

    **Authentication required:** Valid JWT token

    **Possible errors:**
    - `404 Not Found` : Author does not exist
    """,
    responses={
        204: {"description": "Author deleted successfully"},
        404: {"description": "Author not found"},
        401: {"description": "Unauthorized"},
    },
)
async def delete_author(
    author_id: int,
    service: AuthorService = Depends(get_author_service),
    user=Depends(get_current_user),
):
    await service.delete_author(author_id)
