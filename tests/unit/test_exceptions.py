from app.core.exceptions import AppException, ConflictException, NotFoundException, UnauthorizedException


def test_exceptions_construction():
    base = AppException("oops", 418)
    assert str(base) == "oops"
    assert base.status_code == 418
    assert NotFoundException().status_code == 404
    assert ConflictException().status_code == 409
    assert UnauthorizedException().status_code == 401
