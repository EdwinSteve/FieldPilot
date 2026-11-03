"""FastAPI dependency: the container built at startup. The caller is in app/api/auth.py."""

from typing import Annotated

from fastapi import Depends, Request

from app.container import Container


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]
