"""Domain models: Guest, TimeSlot, Table and Booking.

Every attribute is private and exposed through properties, so objects
can never be put into an invalid state (encapsulation + validation).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from enum import Enum
from itertools import count

from exceptions import ValidationError

MAX_SEATS = 20  # largest table the restaurant can have


class Guest:
    """A person who books (or walks in to) the restaurant."""

    _PHONE_PATTERN = re.compile(r"^\+?[\d\s\-()]{6,20}$")

    def __init__(self, name: str, phone: str):
        self.name = name
        self.phone = phone

    @classmethod
    def walk_in(cls, name: str = "") -> "Guest":
        """Create a guest without booking; name and phone are optional."""
        guest = cls.__new__(cls)  # bypass validation: walk-ins have no phone
        guest._name = name.strip() or "Walk-in guests"
        guest._phone = "-"
        return guest

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        value = (value or "").strip()
        if len(value) < 2:
            raise ValidationError("Guest name must have at least 2 characters.")
        self._name = value

    @property
    def phone(self) -> str:
        return self._phone

    @phone.setter
    def phone(self, value: str) -> None:
        value = (value or "").strip()
        if not self._PHONE_PATTERN.match(value):
            raise ValidationError("Enter a valid phone number (digits, spaces, + - ( ) allowed).")
        self._phone = value


class TimeSlot:
    """Immutable period of time [start, end) used by bookings."""

    def __init__(self, start: datetime, end: datetime):
        if end <= start:
            raise ValidationError("The end time must be later than the start time.")
        self._start = start
        self._end = end

    @property
    def start(self) -> datetime:
        return self._start

    @property
    def end(self) -> datetime:
        return self._end

    @property
    def duration(self) -> timedelta:
        return self._end - self._start

    def overlaps(self, other: "TimeSlot") -> bool:
        """True if the two periods share any moment."""
        return self._start < other._end and other._start < self._end

    def contains(self, moment: datetime) -> bool:
        return self._start <= moment < self._end

    def ending_at(self, moment: datetime) -> "TimeSlot":
        """Return a copy of this slot cut short at `moment`."""
        return TimeSlot(self._start, moment)

    def __str__(self) -> str:
        same_day = self._start.date() == self._end.date()
        end_text = self._end.strftime("%H:%M" if same_day else "%d %b %H:%M")
        return f"{self._start.strftime('%d %b %H:%M')} – {end_text}"


class Table:
    """A physical table with a name and a number of seats."""

    _ids = count(1)  # shared counter that gives every table a unique id

    def __init__(self, name: str, seats: int):
        self._id = next(Table._ids)
        self.name = name
        self.seats = seats

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        value = (value or "").strip()
        if not value:
            raise ValidationError("Table name cannot be empty.")
        if len(value) > 30:
            raise ValidationError("Table name is too long (30 characters max).")
        self._name = value

    @property
    def seats(self) -> int:
        return self._seats

    @seats.setter
    def seats(self, value: int) -> None:
        if not isinstance(value, int) or not 1 <= value <= MAX_SEATS:
            raise ValidationError(f"Seats must be a whole number from 1 to {MAX_SEATS}.")
        self._seats = value

    def __str__(self) -> str:
        return f"{self._name} ({self._seats} seats)"


class BookingStatus(Enum):
    """Where a booking is in time, relative to 'now'."""
    UPCOMING = "Upcoming"
    ACTIVE = "Seated now"
    FINISHED = "Finished"


class Booking:
    """A guest, a table and a time slot. Walk-ins are bookings that start now."""

    _ids = count(1)

    def __init__(self, guest: Guest, table: Table, slot: TimeSlot,
                 party_size: int, is_walk_in: bool = False):
        if not 1 <= party_size <= table.seats:
            raise ValidationError(
                f"{table.name} has {table.seats} seats; party size must be 1–{table.seats}.")
        self._id = next(Booking._ids)
        self._guest = guest
        self._table = table
        self._slot = slot
        self._party_size = party_size
        self._is_walk_in = is_walk_in

    @property
    def id(self) -> int:
        return self._id

    @property
    def guest(self) -> Guest:
        return self._guest

    @property
    def table(self) -> Table:
        return self._table

    @property
    def slot(self) -> TimeSlot:
        return self._slot

    @property
    def party_size(self) -> int:
        return self._party_size

    @property
    def is_walk_in(self) -> bool:
        return self._is_walk_in

    def status(self, now: datetime) -> BookingStatus:
        if now < self._slot.start:
            return BookingStatus.UPCOMING
        if self._slot.contains(now):
            return BookingStatus.ACTIVE
        return BookingStatus.FINISHED

    def finish_now(self, now: datetime) -> None:
        """Release the table: shorten the booking so it ends at `now`."""
        self._slot = self._slot.ending_at(now)
