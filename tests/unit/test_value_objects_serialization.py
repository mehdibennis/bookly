from app.domain.entities import AuthorEntity
from app.domain.value_objects import PaginatedResult, PaginationMeta


def test_paginatedresult_to_from_primitive_without_converter():
    meta = PaginationMeta(total=2, page=1, size=10, count=2)
    pr = PaginatedResult(data=[{"id": 1}, {"id": 2}], meta=meta)

    prim = pr.to_primitive()
    assert isinstance(prim, dict)
    assert prim["meta"]["total"] == 2

    recreated = PaginatedResult.from_primitive(prim)
    assert recreated.meta.total == 2
    assert isinstance(recreated.data, list)


def _author_from_dict(d: dict) -> AuthorEntity:
    return AuthorEntity(
        id=d["id"],
        first_name=d.get("first_name", ""),
        last_name=d.get("last_name", ""),
        nationality=None,
        birth_date=None,
        death_date=None,
        bio=None,
        photo_url=None,
    )


def test_paginatedresult_to_from_primitive_with_converter():
    authors = [
        AuthorEntity(
            id=1,
            first_name="A",
            last_name="B",
            nationality=None,
            birth_date=None,
            death_date=None,
            bio=None,
            photo_url=None,
        ),
    ]
    meta = PaginationMeta(total=1, page=1, size=10, count=1)
    pr = PaginatedResult(data=authors, meta=meta)

    prim = pr.to_primitive(
        item_converter=lambda a: {"id": a.id, "first_name": a.first_name}
    )
    assert prim["data"][0]["first_name"] == "A"

    recreated = PaginatedResult.from_primitive(prim, item_converter=_author_from_dict)
    assert recreated.meta.count == 1
    assert recreated.data[0].id == 1
