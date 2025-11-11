from fastapi import FastAPI


def reverse(app: FastAPI, name: str, **path_params: object) -> str:
    """Django-like reverse() for FastAPI route names.

    Usage:
        path = reverse(app, "books:get", book_id=1)
    """
    return app.url_path_for(name, **path_params)
