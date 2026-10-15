"""Errores del dominio. El borde HTTP los traduce a {message, error_id, code}."""


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class LegacyUnavailable(Exception):
    """La base legacy no responde (caída, red, timeout o circuito abierto)."""


class LegacyError(Exception):
    """La base respondió, pero con un error inesperado (nunca se expone al cliente)."""


def not_found(message="Recurso no encontrado"):
    return ApiError(404, "NOT_FOUND", message)


def validation(message):
    return ApiError(400, "VALIDATION_ERROR", message)
