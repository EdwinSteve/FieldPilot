"""Authorisation rules on top of a verified Principal (§4.12 rule 8)."""

from collections.abc import Callable

from app.identity.errors import ForbiddenError
from app.identity.models import FARM_ROLES, Principal, Role
from app.persistence.ports import UnitOfWork

UowFactory = Callable[[], UnitOfWork]


class AccessPolicy:
    def __init__(self, uow: UowFactory) -> None:
        self._uow = uow

    def require_farm(self, principal: Principal, plot_id: int | None = None) -> None:
        """Farm routes: the farmer or admin role, and membership of the plot they name."""
        if principal.role not in FARM_ROLES:
            raise ForbiddenError("Esta sección es solo para agricultores.")
        if plot_id is None or principal.sees_every_plot or principal.user_id is None:
            return
        with self._uow() as uow:
            uow.plots.get(plot_id)  # an unknown plot stays a 404
            if not uow.plot_members.is_member(plot_id, principal.user_id):
                raise ForbiddenError("No tienes acceso a esta parcela.")

    def require_admin(self, principal: Principal) -> None:
        if principal.role is not Role.ADMIN:
            raise ForbiddenError("Solo un administrador puede hacer esto.")

    def add_member(self, principal: Principal, plot_id: int, user_id: int) -> None:
        self.require_admin(principal)
        with self._uow() as uow:
            uow.plots.get(plot_id)
            uow.users.get(user_id)
            uow.plot_members.add(plot_id, user_id)
            uow.commit()
