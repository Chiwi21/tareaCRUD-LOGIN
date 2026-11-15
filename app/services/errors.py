"""Errores de dominio que los routers traducen a mensajes de formulario."""


class DomainError(Exception):
    pass


class ValidationError(DomainError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class NotFoundError(DomainError):
    pass
