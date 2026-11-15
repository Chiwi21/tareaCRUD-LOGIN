"""Mensajes flash basados en la sesión firmada de Starlette."""

from __future__ import annotations

from fastapi import Request


def flash(request: Request, message: str, category: str = "success") -> None:
    request.session.setdefault("_flashes", []).append(
        {"message": message, "category": category}
    )


def get_flashed_messages(request: Request) -> list[dict[str, str]]:
    return request.session.pop("_flashes", [])
