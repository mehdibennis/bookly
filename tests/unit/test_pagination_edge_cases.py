import pytest

from app.domain.value_objects import PaginatedResult, PaginationMeta, PaginationParams


def test_pagination_params_validation():
    with pytest.raises(ValueError):
        PaginationParams(page=0, size=10)

    with pytest.raises(ValueError):
        PaginationParams(page=1, size=0)

    with pytest.raises(ValueError):
        PaginationParams(page=1, size=101)


def test_paginated_result_from_primitive_missing_meta():
    primitive = {"data": [], "meta": {}}
    result = PaginatedResult.from_primitive(primitive)
    assert isinstance(result, PaginatedResult)
    assert result.meta.page == 1
    assert result.meta.size == 0 or isinstance(result.meta.size, int)


def test_paginated_result_last_next_previous_pages():
    meta = PaginationMeta(total=25, page=2, size=10, count=10)
    items = [1, 2, 3]
    result = PaginatedResult(data=items, meta=meta)
    assert result.meta.last_page == 3
    assert result.meta.next_page == 3
    assert result.meta.previous_page == 1
