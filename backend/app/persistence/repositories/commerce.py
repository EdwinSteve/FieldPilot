"""Repositories for the market: warehouses, listings, customers and orders (§4.15, D085)."""

from collections.abc import Sequence
from datetime import datetime

from sqlmodel import Session, col, func, select

from app.market.models import (
    CartItem,
    CartProposal,
    CustomerOrder,
    CustomerProfile,
    Listing,
    ListingStatus,
    Offer,
    OrderLine,
    OrderStatus,
    Payout,
    PriceBreakdown,
    ProposalStatus,
    Shipment,
    StockMovement,
    StockReason,
    Warehouse,
)
from app.persistence.repositories._base import get_row_or_raise, insert
from app.persistence.tables import (
    CartItemRow,
    CartProposalRow,
    CustomerOrderRow,
    CustomerProfileRow,
    ListingRow,
    OfferRow,
    OrderLineRow,
    PayoutRow,
    ShipmentRow,
    StockMovementRow,
    WarehouseRow,
)


class SqlWarehouseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, warehouse: Warehouse) -> Warehouse:
        row = WarehouseRow(
            code=warehouse.code,
            name=warehouse.name,
            municipality=warehouse.municipality,
            department=warehouse.department,
            cold_storage=warehouse.cold_storage,
        )
        return _warehouse(insert(self._session, row))

    def get(self, warehouse_id: int) -> Warehouse:
        return _warehouse(get_row_or_raise(self._session, WarehouseRow, warehouse_id, "Warehouse"))

    def find_by_code(self, code: str) -> Warehouse | None:
        row = self._session.exec(select(WarehouseRow).where(WarehouseRow.code == code)).first()
        return None if row is None else _warehouse(row)

    def list(self) -> Sequence[Warehouse]:
        rows = self._session.exec(select(WarehouseRow).order_by(col(WarehouseRow.id)))
        return [_warehouse(row) for row in rows]


class SqlListingRepository:
    """Listings with their shipment, stock ledger and offers: one aggregate."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, listing: Listing) -> Listing:
        return _listing(insert(self._session, _listing_row(listing)))

    def get(self, listing_id: int) -> Listing:
        return _listing(get_row_or_raise(self._session, ListingRow, listing_id, "Listing"))

    def find_by_lot(self, lot_code: str) -> Listing | None:
        row = self._session.exec(select(ListingRow).where(ListingRow.lot_code == lot_code)).first()
        return None if row is None else _listing(row)

    def list(
        self, status: ListingStatus | None = None, farmer_id: int | None = None
    ) -> Sequence[Listing]:
        query = select(ListingRow).order_by(col(ListingRow.id))
        if status is not None:
            query = query.where(ListingRow.status == status.value)
        if farmer_id is not None:
            query = query.where(ListingRow.farmer_id == farmer_id)
        return [_listing(row) for row in self._session.exec(query)]

    def set_status(self, listing_id: int, status: ListingStatus) -> Listing:
        row = get_row_or_raise(self._session, ListingRow, listing_id, "Listing")
        row.status = status.value
        self._session.add(row)
        self._session.flush()
        return _listing(row)

    def add_shipment(self, shipment: Shipment) -> Shipment:
        row = ShipmentRow(
            listing_id=shipment.listing_id,
            warehouse_id=shipment.warehouse_id,
            dispatched_g=shipment.dispatched_g,
            dispatched_at=shipment.dispatched_at,
        )
        return _shipment(insert(self._session, row))

    def get_shipment(self, shipment_id: int) -> Shipment:
        return _shipment(get_row_or_raise(self._session, ShipmentRow, shipment_id, "Shipment"))

    def shipment_for(self, listing_id: int) -> Shipment | None:
        query = select(ShipmentRow).where(ShipmentRow.listing_id == listing_id)
        row = self._session.exec(query).first()
        return None if row is None else _shipment(row)

    def record_receipt(self, shipment: Shipment) -> Shipment:
        if shipment.id is None:
            raise ValueError("shipment was not stored")
        row = get_row_or_raise(self._session, ShipmentRow, shipment.id, "Shipment")
        row.received_g, row.temperature_c = shipment.received_g, shipment.temperature_c
        row.received_at, row.received_by = shipment.received_at, shipment.received_by
        self._session.add(row)
        self._session.flush()
        return _shipment(row)

    def move_stock(self, movement: StockMovement) -> None:
        insert(
            self._session,
            StockMovementRow(
                listing_id=movement.listing_id,
                delta_g=movement.delta_g,
                reason=movement.reason.value,
                ref=movement.ref,
                occurred_at=movement.occurred_at,
            ),
        )

    def stock_g(self, listing_id: int) -> int:
        query = select(func.coalesce(func.sum(StockMovementRow.delta_g), 0)).where(
            StockMovementRow.listing_id == listing_id
        )
        return int(self._session.exec(query).one())

    def moved_g(self, listing_id: int, reason: StockReason) -> int:
        """The grams of one reason, as a positive amount (sold grams, released grams…)."""
        query = select(func.coalesce(func.sum(StockMovementRow.delta_g), 0)).where(
            StockMovementRow.listing_id == listing_id, StockMovementRow.reason == reason.value
        )
        return abs(int(self._session.exec(query).one()))

    def add_offer(self, offer: Offer) -> Offer:
        row = OfferRow(
            listing_id=offer.listing_id,
            discount_pct=offer.discount_pct,
            starts_on=offer.starts_on,
            ends_on=offer.ends_on,
            created_at=offer.created_at,
        )
        return _offer(insert(self._session, row))

    def offers(self, listing_id: int | None = None) -> Sequence[Offer]:
        query = select(OfferRow).order_by(col(OfferRow.id))
        if listing_id is not None:
            query = query.where(OfferRow.listing_id == listing_id)
        return [_offer(row) for row in self._session.exec(query)]


class SqlCustomerRepository:
    """A customer's profile, cart and the assistant's proposals."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def profile(self, user_id: int) -> CustomerProfile:
        row = self._session.get(CustomerProfileRow, user_id)
        if row is None:
            return CustomerProfile(user_id)
        return CustomerProfile(row.user_id, row.delivery_address, row.consent_profiling_at)

    def save_profile(self, profile: CustomerProfile) -> CustomerProfile:
        row = self._session.get(CustomerProfileRow, profile.user_id) or CustomerProfileRow(
            user_id=profile.user_id
        )
        row.delivery_address = profile.delivery_address
        row.consent_profiling_at = profile.consent_profiling_at
        self._session.add(row)
        self._session.flush()
        return profile

    def cart(self, customer_id: int) -> Sequence[CartItem]:
        query = (
            select(CartItemRow)
            .where(CartItemRow.customer_id == customer_id)
            .order_by(col(CartItemRow.id))
        )
        return [
            CartItem(row.customer_id, row.listing_id, row.quantity_kg, row.id)
            for row in self._session.exec(query)
        ]

    def set_cart_item(self, customer_id: int, listing_id: int, quantity_kg: int) -> None:
        """Quantity 0 removes the line."""
        row = self._session.exec(
            select(CartItemRow).where(
                CartItemRow.customer_id == customer_id, CartItemRow.listing_id == listing_id
            )
        ).first()
        if quantity_kg == 0:
            if row is not None:
                self._session.delete(row)
        elif row is None:
            self._session.add(
                CartItemRow(customer_id=customer_id, listing_id=listing_id, quantity_kg=quantity_kg)
            )
        else:
            row.quantity_kg = quantity_kg
            self._session.add(row)
        self._session.flush()

    def clear_cart(self, customer_id: int) -> None:
        for row in self._session.exec(
            select(CartItemRow).where(CartItemRow.customer_id == customer_id)
        ):
            self._session.delete(row)
        self._session.flush()

    def add_proposal(self, proposal: CartProposal) -> CartProposal:
        row = CartProposalRow(
            customer_id=proposal.customer_id,
            items=[dict(item) for item in proposal.items],
            note=proposal.note,
            status=proposal.status.value,
            run_id=proposal.run_id,
            created_at=proposal.created_at,
        )
        return _proposal(insert(self._session, row))

    def proposal(self, proposal_id: int) -> CartProposal:
        row = get_row_or_raise(self._session, CartProposalRow, proposal_id, "CartProposal")
        return _proposal(row)

    def set_proposal_status(self, proposal_id: int, status: ProposalStatus) -> None:
        row = get_row_or_raise(self._session, CartProposalRow, proposal_id, "CartProposal")
        row.status = status.value
        self._session.add(row)
        self._session.flush()


class SqlOrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, order: CustomerOrder) -> CustomerOrder:
        row = insert(
            self._session,
            CustomerOrderRow(
                customer_id=order.customer_id,
                status=order.status.value,
                total_minor=order.total_minor,
                currency=order.currency,
                payment_ref=order.payment_ref,
                delivery_address=order.delivery_address,
                placed_at=order.placed_at,
            ),
        )
        if row.id is None:
            raise ValueError("order was not stored")
        for line in order.lines:
            insert(self._session, _line_row(row.id, line))
        return self.get(row.id)

    def get(self, order_id: int) -> CustomerOrder:
        row = get_row_or_raise(self._session, CustomerOrderRow, order_id, "Order")
        return self._order(row)

    def list(self, customer_id: int | None = None) -> Sequence[CustomerOrder]:
        query = select(CustomerOrderRow).order_by(col(CustomerOrderRow.placed_at).desc())
        if customer_id is not None:
            query = query.where(CustomerOrderRow.customer_id == customer_id)
        return [self._order(row) for row in self._session.exec(query)]

    def set_status(self, order_id: int, status: OrderStatus, at: datetime) -> CustomerOrder:
        row = get_row_or_raise(self._session, CustomerOrderRow, order_id, "Order")
        row.status = status.value
        if status is OrderStatus.DELIVERED:
            row.delivered_at = at
        if status is OrderStatus.CANCELLED:
            row.cancelled_at = at
        self._session.add(row)
        self._session.flush()
        return self._order(row)

    def add_payout(self, payout: Payout) -> None:
        insert(
            self._session,
            PayoutRow(
                order_line_id=payout.order_line_id,
                farmer_id=payout.farmer_id,
                amount_minor=payout.amount_minor,
                currency=payout.currency,
                created_at=payout.created_at,
            ),
        )

    def payouts_minor(self, listing_id: int) -> int:
        query = (
            select(func.coalesce(func.sum(PayoutRow.amount_minor), 0))
            .join(OrderLineRow, col(OrderLineRow.id) == col(PayoutRow.order_line_id))
            .where(OrderLineRow.listing_id == listing_id)
        )
        return int(self._session.exec(query).one())

    def _order(self, row: CustomerOrderRow) -> CustomerOrder:
        if row.id is None:
            raise ValueError("order was not stored")
        lines = self._session.exec(
            select(OrderLineRow)
            .where(OrderLineRow.order_id == row.id)
            .order_by(col(OrderLineRow.id))
        )
        return CustomerOrder(
            customer_id=row.customer_id,
            status=OrderStatus(row.status),
            total_minor=row.total_minor,
            currency=row.currency,
            payment_ref=row.payment_ref,
            delivery_address=row.delivery_address,
            placed_at=row.placed_at,
            lines=tuple(_line(line) for line in lines),
            delivered_at=row.delivered_at,
            cancelled_at=row.cancelled_at,
            id=row.id,
        )


def _warehouse(row: WarehouseRow) -> Warehouse:
    return Warehouse(row.code, row.name, row.municipality, row.department, row.cold_storage, row.id)


def _listing_row(listing: Listing) -> ListingRow:
    return ListingRow(
        lot_code=listing.lot_code,
        farmer_id=listing.farmer_id,
        warehouse_id=listing.warehouse_id,
        crop=listing.crop,
        quantity_g=listing.quantity_g,
        farmer_price_minor=listing.farmer_price_minor,
        currency=listing.currency,
        status=listing.status.value,
        created_at=listing.created_at,
    )


def _listing(row: ListingRow) -> Listing:
    return Listing(
        lot_code=row.lot_code,
        farmer_id=row.farmer_id,
        warehouse_id=row.warehouse_id,
        crop=row.crop,
        quantity_g=row.quantity_g,
        farmer_price_minor=row.farmer_price_minor,
        currency=row.currency,
        status=ListingStatus(row.status),
        created_at=row.created_at,
        id=row.id,
    )


def _shipment(row: ShipmentRow) -> Shipment:
    return Shipment(
        listing_id=row.listing_id,
        warehouse_id=row.warehouse_id,
        dispatched_g=row.dispatched_g,
        dispatched_at=row.dispatched_at,
        received_g=row.received_g,
        temperature_c=row.temperature_c,
        received_at=row.received_at,
        received_by=row.received_by,
        id=row.id,
    )


def _offer(row: OfferRow) -> Offer:
    return Offer(
        row.listing_id, row.discount_pct, row.starts_on, row.ends_on, row.created_at, row.id
    )


def _proposal(row: CartProposalRow) -> CartProposal:
    return CartProposal(
        customer_id=row.customer_id,
        items=tuple(row.items),
        note=row.note,
        status=ProposalStatus(row.status),
        created_at=row.created_at,
        id=row.id,
        run_id=row.run_id,
    )


def _line_row(order_id: int, line: OrderLine) -> OrderLineRow:
    return OrderLineRow(
        order_id=order_id,
        listing_id=line.listing_id,
        lot_code=line.lot_code,
        farmer_id=line.farmer_id,
        crop=line.crop,
        quantity_kg=line.quantity_kg,
        farmer_minor=line.price.farmer_minor,
        logistics_minor=line.price.logistics_minor,
        platform_minor=line.price.platform_minor,
        discount_pct=line.price.discount_pct,
        currency=line.price.currency,
    )


def _line(row: OrderLineRow) -> OrderLine:
    price = PriceBreakdown(
        row.farmer_minor, row.logistics_minor, row.platform_minor, row.discount_pct, row.currency
    )
    return OrderLine(
        listing_id=row.listing_id,
        lot_code=row.lot_code,
        farmer_id=row.farmer_id,
        crop=row.crop,
        quantity_kg=row.quantity_kg,
        price=price,
        id=row.id,
        order_id=row.order_id,
    )
