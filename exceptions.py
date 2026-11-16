"""Custom exceptions for the restaurant booking application.

A dedicated hierarchy lets the UI catch one base class (RestaurantError)
and show a friendly message instead of crashing.
"""


class RestaurantError(Exception):
    """Base class for every error raised by the business logic."""


class ValidationError(RestaurantError):
    """Raised when user input (name, phone, seats, time...) is invalid."""


class DuplicateTableError(RestaurantError):
    """Raised when a table with the same name already exists."""


class TableNotFoundError(RestaurantError):
    """Raised when a table id is unknown."""


class BookingNotFoundError(RestaurantError):
    """Raised when a booking id is unknown."""


class BookingConflictError(RestaurantError):
    """Raised when a table is already booked for the requested time."""


class TableInUseError(RestaurantError):
    """Raised when a table cannot be changed/removed because of active or upcoming bookings."""
