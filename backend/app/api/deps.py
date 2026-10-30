"""FastAPI dependencies: the container built at startup, and the acting person."""

from typing import Annotated

from fastapi import Depends, Request

from app.container import Container

# No authentication yet: every request comes from the farmer's dashboard.
FARMER = "farmer:dashboard"


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]
