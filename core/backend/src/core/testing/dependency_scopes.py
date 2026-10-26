"""Which scope each route opens a ``yield`` dependency at.

Guards the request session (``get_repo``): the default chain must open it at
``scope="function"`` (commit before the response is sent), streaming endpoints at request scope,
and no route may reach it at both scopes. FastAPI caches the two scopes under different keys,
so such a route would open two sessions and can block on its own row locks.

Reads the route table only (no requests, no database). ``app.dependency_overrides`` are
followed the way FastAPI resolves them, so a core router's ``Depends(get_services)`` is walked
through the app's override.
"""

from collections.abc import Callable, Iterator, Sequence
from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import get_dependant
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute


def iter_api_routes(routes: Sequence[BaseRoute]) -> Iterator[APIRoute]:
    """Every ``APIRoute``, descending into included routers (Starlette 1.x) and mounts."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
            continue
        nested = getattr(route, "routes", None)
        if nested is None:
            original = getattr(route, "original_router", None)
            nested = getattr(original, "routes", None) if original is not None else None
        if nested:
            yield from iter_api_routes(nested)


def dependency_scopes(app: FastAPI, route: APIRoute, dependency: Callable[..., Any]) -> set[str]:
    """The scopes (``"function"`` / ``"request"``) at which ``route`` reaches ``dependency``.

    Empty when the route never reaches it. A bare ``Depends(dependency)`` counts as
    ``"request"``: that is the exit stack FastAPI puts a ``yield`` dependency on by default.
    """
    overrides = app.dependency_overrides
    scopes: set[str] = set()

    def walk(dependant: Dependant) -> None:
        for sub in dependant.dependencies:
            if sub.call is dependency:
                scopes.add("function" if sub.scope == "function" else "request")
            if sub.call in overrides:
                sub = get_dependant(path=route.path_format, call=overrides[sub.call], scope=sub.scope)
            walk(sub)

    walk(route.dependant)
    return scopes


def dependency_scopes_by_route(app: FastAPI, dependency: Callable[..., Any]) -> list[tuple[APIRoute, set[str]]]:
    """``(route, scopes)`` for every route that reaches ``dependency`` (routes aren't hashable)."""
    result: list[tuple[APIRoute, set[str]]] = []
    for route in iter_api_routes(app.routes):
        scopes = dependency_scopes(app, route, dependency)
        if scopes:
            result.append((route, scopes))
    return result
