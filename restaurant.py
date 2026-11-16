"""Restaurant: the single entry point for all business rules.

The UI never edits tables or bookings directly; it asks the Restaurant,
which validates everything and keeps the data consistent.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from exceptions import (BookingConflictError, BookingNotFoundError, DuplicateTableError,
                        TableInUseError, TableNotFoundError, ValidationError)
from models import Booking, BookingStatus, Guest, Table, TimeSlot

RESERVED_SOON_WINDOW = timedelta(minutes=60)  # table shows "Reserved" this long before a booking


class TableState(Enum):
    """Live state of a table shown on the status page."""
    FREE = "Free"
    RESERVED_SOON = "Reserved soon"
    OCCUPIED = "Occupied"


class Restaurant:
    """Owns the tables and bookings and enforces the rules between them."""

    def __init__(self, name: str):
        self._name = name
        self._tables: dict[int, Table] = {}
        self._bookings: dict[int, Booking] = {}

    @property
    def name(self) -> str:
        return self._name

    # ------------------------------------------------------------ tables
    @property
    def tables(self) -> list[Table]:
        """All tables sorted by name (a copy, so callers cannot break the data)."""
        return sorted(self._tables.values(), key=lambda t: t.name.lower())

    def get_table(self, table_id: int) -> Table:
        try:
            return self._tables[table_id]
        except KeyError:
            raise TableNotFoundError("This table no longer exists.") from None

    def _ensure_name_is_unique(self, name: str, ignore_id: Optional[int] = None) -> None:
        for table in self._tables.values():
            if table.id != ignore_id and table.name.lower() == name.strip().lower():
                raise DuplicateTableError(f"A table named '{name.strip()}' already exists.")

    def add_table(self, name: str, seats: int) -> Table:
        table = Table(name, seats)  # validates input
        self._ensure_name_is_unique(table.name)
        self._tables[table.id] = table
        return table

    def update_table(self, table_id: int, name: str, seats: int) -> None:
        table = self.get_table(table_id)
        self._ensure_name_is_unique(name, ignore_id=table_id)
        largest_party = max((b.party_size for b in self._unfinished_bookings(table)), default=0)
        if seats < largest_party:
            raise TableInUseError(
                f"{table.name} has a booking for {largest_party} guests; seats cannot go below that.")
        # Validate both values on a throw-away table first so we never half-update.
        Table(name, seats)
        table.name = name
        table.seats = seats

    def remove_table(self, table_id: int) -> None:
        table = self.get_table(table_id)
        if self._unfinished_bookings(table):
            raise TableInUseError(
                f"{table.name} has active or upcoming bookings. Cancel them before deleting the table.")
        for booking in [b for b in self._bookings.values() if b.table is table]:
            del self._bookings[booking.id]  # drop its history together with the table
        del self._tables[table_id]

    # ---------------------------------------------------------- bookings
    @property
    def bookings(self) -> list[Booking]:
        """All bookings sorted by start time."""
        return sorted(self._bookings.values(), key=lambda b: b.slot.start)

    def bookings_for(self, table: Table) -> list[Booking]:
        return [b for b in self.bookings if b.table is table]

    def _unfinished_bookings(self, table: Table, now: Optional[datetime] = None) -> list[Booking]:
        now = now or datetime.now()
        return [b for b in self.bookings_for(table) if b.status(now) != BookingStatus.FINISHED]

    def is_table_free(self, table: Table, slot: TimeSlot) -> bool:
        return not any(b.slot.overlaps(slot) for b in self.bookings_for(table))

    def available_tables(self, slot: TimeSlot, party_size: int = 1) -> list[Table]:
        """Tables that are big enough and not booked during `slot` (smallest first)."""
        found = [t for t in self.tables if t.seats >= party_size and self.is_table_free(t, slot)]
        return sorted(found, key=lambda t: (t.seats, t.name.lower()))

    def create_booking(self, guest: Guest, table_id: int, slot: TimeSlot,
                       party_size: int, is_walk_in: bool = False) -> Booking:
        table = self.get_table(table_id)
        if not is_walk_in and slot.end <= datetime.now():
            raise ValidationError("The booking must end in the future.")
        if not self.is_table_free(table, slot):
            raise BookingConflictError(f"{table.name} is already booked during {slot}.")
        booking = Booking(guest, table, slot, party_size, is_walk_in)
        self._bookings[booking.id] = booking
        return booking

    def seat_walk_in(self, table_id: int, party_size: int, minutes: int = 90,
                     guest_name: str = "") -> Booking:
        """Take a table right now for guests who came without a booking."""
        now = datetime.now().replace(microsecond=0)
        if minutes < 15:
            raise ValidationError("A visit must last at least 15 minutes.")
        slot = TimeSlot(now, now + timedelta(minutes=minutes))
        return self.create_booking(Guest.walk_in(guest_name), table_id, slot,
                                   party_size, is_walk_in=True)

    def _get_booking(self, booking_id: int) -> Booking:
        try:
            return self._bookings[booking_id]
        except KeyError:
            raise BookingNotFoundError("This booking no longer exists.") from None

    def cancel_booking(self, booking_id: int) -> None:
        self._get_booking(booking_id)
        del self._bookings[booking_id]

    def release_table(self, booking_id: int) -> None:
        """Guests have left: end an active booking now so the table is free again."""
        booking = self._get_booking(booking_id)
        now = datetime.now().replace(microsecond=0)
        if booking.status(now) != BookingStatus.ACTIVE:
            raise ValidationError("Only a booking that is in progress can be released.")
        if now <= booking.slot.start:
            self.cancel_booking(booking_id)  # started this very second: nothing to keep
        else:
            booking.finish_now(now)

    # ------------------------------------------------------------ status
    def current_booking(self, table: Table, now: Optional[datetime] = None) -> Optional[Booking]:
        now = now or datetime.now()
        return next((b for b in self.bookings_for(table) if b.status(now) == BookingStatus.ACTIVE), None)

    def next_booking(self, table: Table, now: Optional[datetime] = None) -> Optional[Booking]:
        now = now or datetime.now()
        return next((b for b in self.bookings_for(table) if b.status(now) == BookingStatus.UPCOMING), None)

    def table_state(self, table: Table, now: Optional[datetime] = None) -> TableState:
        now = now or datetime.now()
        if self.current_booking(table, now):
            return TableState.OCCUPIED
        upcoming = self.next_booking(table, now)
        if upcoming and upcoming.slot.start - now <= RESERVED_SOON_WINDOW:
            return TableState.RESERVED_SOON
        return TableState.FREE

    def count_by_state(self, now: Optional[datetime] = None) -> dict[TableState, int]:
        now = now or datetime.now()
        totals = {state: 0 for state in TableState}
        for table in self._tables.values():
            totals[self.table_state(table, now)] += 1
        return totals
