from fastapi import status


class AppException(Exception):
    """Exception de base pour l’application."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Ressource non trouvée."):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ConflictException(AppException):
    def __init__(self, message: str = "Conflit : ressource déjà existante."):
        super().__init__(message, status.HTTP_409_CONFLICT)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Non autorisé."):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Accès interdit."):
        super().__init__(message, status.HTTP_403_FORBIDDEN)
