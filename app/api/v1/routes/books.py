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
    summary="Paginated list of books",
    description="""
    Get the complete list of books with pagination.

    **Pagination parameters :**
    - `page` : Page number (>=1)
    - `size` : Number of items per page (1-100)
    **Example response :**
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

    **Note :** This endpoint is public (no authentication required).
    """,
    response_description="Paginated list of books with pagination metadata",
    responses={
        200: {"description": "Books retrieved successfully"},
    },
)
async def list_books(
    page: int = Query(1, ge=1, description="Page number (>=1)", example=1),
    size: int = Query(10, ge=1, le=100, description="Page size (1-100)", example=10),
    book_service: BookService = Depends(get_book_service),
):
    """Get the paginated list of books (pagination page/size)."""
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
    summary="Get a book by ID",
    description="""
    Get the full details of a specific book.

    **Authentication required:** Valid JWT token

    **Possible errors:**
    - `401 Unauthorized` : Missing or invalid token
    - `404 Not Found` : Book does not exist
    """,
    responses={
        404: {"description": "Book not found"},
        401: {"description": "Unauthorized"},
        200: {"description": "Book retrieved successfully"},
    },
)
async def get_book(
    book_id: int,
    book_service: BookService = Depends(get_book_service),
    user=Depends(get_current_user),
):
    """Get a book by its ID."""
    book = await book_service.get_book(book_id)
    return BookMapper.entity_to_dto(book)


# --- CREATE ---
@router.post(
    "/",
    response_model=Book,
    status_code=status.HTTP_201_CREATED,
    name="books:create",
    summary="Create a new book",
    description="""
    Create a new book in the collection.

    **Authentication required:** Valid JWT token
    **Validation rules:**
    - Title and author cannot be empty
    - Title is normalized (automatic capitalization)
    - Duplicate titles are not allowed
    **Possible errors:**
    - `400 Bad Request` : Invalid data
    - `409 Conflict` : Book with this title already exists
    """,
    responses={
        201: {"description": "Book created successfully"},
        400: {"description": "Invalid data"},
        409: {"description": "Conflict: existing book"},
        401: {"description": "Unauthorized"},
    },
)
async def create_book(
    book_in: BookCreate,
    book_service: BookService = Depends(get_book_service),
    user=Depends(get_current_user),
):
    """Create a new book."""
    book_data = BookMapper.create_dto_to_domain(book_in)
    book = await book_service.create_book(book_data)
    return BookMapper.entity_to_dto(book)


# --- PARTIAL UPDATE (PATCH) ---
@router.patch(
    "/{book_id}",
    response_model=Book,
    name="books:update",
    summary="Book partial update",
    description="""
    Update book information.
    **Authentication required:** Valid JWT token

    **Partial update:** All fields are optional.

    **Possible errors:**
    - `404 Not Found` : Book does not exist
    - `409 Conflict` : Title conflicts with another book
    """,
    responses={
        200: {"description": "Book partially updated"},
        404: {"description": "Book not found"},
        409: {"description": "Title conflict"},
        401: {"description": "Unauthorized"},
    },
)
async def patch_book(
    book_id: int,
    book_in: BookUpdate,
    book_service: BookService = Depends(get_book_service),
    user=Depends(get_current_user),
):
    """Partially update a book (PATCH semantics)."""
    book_data = BookMapper.update_dto_to_domain(book_in)
    book = await book_service.partial_update_book(book_id, book_data)
    return BookMapper.entity_to_dto(book)


# --- DELETE ---
@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="books:delete",
    summary="Delete a book",
    description="""
    Permanently delete a book from the collection.

    **Authentication required:** Valid JWT token
    **Possible errors:**
    - `404 Not Found` : Book does not exist
    """,
    responses={
        204: {"description": "Book deleted successfully"},
        404: {"description": "Book not found"},
        401: {"description": "Unauthorized"},
    },
)
async def delete_book(
    book_id: int,
    book_service: BookService = Depends(get_book_service),
    user=Depends(get_current_user),
):
    """Delete a book."""
    await book_service.delete_book(book_id)
