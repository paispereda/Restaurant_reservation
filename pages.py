"""UI pages. Each page is a class with a render() method (a small class hierarchy).

Pages only collect input and show data; every rule lives in Restaurant.
"""
from abc import ABC, abstractmethod
from datetime import datetime, time, timedelta
from html import escape

import streamlit as st

from exceptions import RestaurantError
from models import BookingStatus, Guest, TimeSlot
from restaurant import Restaurant, TableState
from styles import STATE_COLORS


class Page(ABC):
    """Base class for all pages: holds the restaurant and shared helpers."""

    title: str = ""

    def __init__(self, restaurant: Restaurant):
        self._restaurant = restaurant

    @abstractmethod
    def render(self) -> None:
        """Draw the page."""

    @staticmethod
    def _flash(kind: str, message: str) -> None:
        """Remember a message to show after the next rerun."""
        st.session_state["flash"] = (kind, message)

    def _run_action(self, action, success_message: str) -> bool:
        """Run a Restaurant action; show an error on failure, a success message otherwise."""
        try:
            action()
        except RestaurantError as error:
            st.error(str(error))
            return False
        self._flash("success", success_message)
        st.rerun()
        return True


class BookingsPage(Page):
    """Create bookings, seat walk-in guests and manage the booking list."""

    title = "Bookings"

    def render(self) -> None:
        st.header("Bookings")
        new_tab, walk_in_tab = st.tabs(["New booking", "Guests without booking"])
        with new_tab:
            self._render_booking_form()
        with walk_in_tab:
            self._render_walk_in_form()
        self._render_booking_list()

    # -- new booking -----------------------------------------------------
    def _render_booking_form(self) -> None:
        # The nonce changes after each success, which gives every widget a fresh key (empty form).
        nonce = st.session_state.setdefault("form_nonce", 0)
        key = lambda name: f"{name}_{nonce}"

        left, right = st.columns(2)
        name = left.text_input("Guest name", key=key("name"))
        phone = right.text_input("Phone number", key=key("phone"))

        c1, c2, c3, c4 = st.columns(4)
        party_size = c1.number_input("Guests", 1, 20, 2, key=key("party"))
        day = c2.date_input("Date", datetime.now().date(), key=key("day"))
        start_t = c3.time_input("From", time(19, 0), step=900, key=key("from"))
        end_t = c4.time_input("To", time(20, 30), step=900, key=key("to"))

        start = datetime.combine(day, start_t)
        end = datetime.combine(day, end_t)
        if end <= start:
            end += timedelta(days=1)  # a visit that runs past midnight

        free_tables = self._restaurant.available_tables(TimeSlot(start, end), int(party_size))
        if not free_tables:
            st.warning("No table is free for this time and party size. Try another time.")
            table_id = None
        else:
            table_id = st.selectbox("Table", [t.id for t in free_tables],
                                    format_func=lambda i: str(self._restaurant.get_table(i)),
                                    key=key("table"))

        if st.button("Book table", type="primary", disabled=table_id is None, key=key("submit")):
            def action():
                guest = Guest(name, phone)
                self._restaurant.create_booking(guest, table_id, TimeSlot(start, end), int(party_size))
                st.session_state["form_nonce"] = nonce + 1
            self._run_action(action, f"Table booked for {name.strip()}.")

    # -- walk-in guests --------------------------------------------------
    def _render_walk_in_form(self) -> None:
        st.caption("Guests arrived without a booking? Take a free table for them right now.")
        now = datetime.now()
        # Tables reserved for later can still be used for a short visit; conflicts are checked on save.
        free_now = [t for t in self._restaurant.tables
                    if self._restaurant.table_state(t, now) != TableState.OCCUPIED]
        if not free_now:
            st.info("No table is free right now. Check the Status page.")
            return

        c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
        table_id = c1.selectbox("Table", [t.id for t in free_now],
                                format_func=lambda i: str(self._restaurant.get_table(i)), key="walk_table")
        party_size = c2.number_input("Guests", 1, 20, 2, key="walk_party")
        minutes = c3.number_input("Minutes", 15, 480, 90, step=15, key="walk_minutes")
        guest_name = c4.text_input("Name (optional)", key="walk_name")
        if st.button("Take table now", type="primary", key="walk_submit"):
            self._run_action(
                lambda: self._restaurant.seat_walk_in(table_id, int(party_size), int(minutes), guest_name),
                "Table taken. Guests are seated.")

    # -- booking list ----------------------------------------------------
    def _render_booking_list(self) -> None:
        st.subheader("Current and upcoming bookings")
        now = datetime.now()
        open_bookings = [b for b in self._restaurant.bookings if b.status(now) != BookingStatus.FINISHED]
        if not open_bookings:
            st.info("No bookings yet. Create one above.")
        for b in open_bookings:
            cols = st.columns([3, 2, 3, 2, 2])
            who = f"**{b.guest.name}**" + ("  (walk-in)" if b.is_walk_in else f"  \n{b.guest.phone}")
            cols[0].markdown(who)
            cols[1].markdown(f"{b.table.name}  \n{b.party_size} guests")
            cols[2].markdown(str(b.slot))
            cols[3].markdown(b.status(now).value)
            if b.status(now) == BookingStatus.ACTIVE:
                if cols[4].button("Release table", key=f"release_{b.id}"):
                    self._run_action(lambda b=b: self._restaurant.release_table(b.id),
                                     f"{b.table.name} is free again.")
            elif cols[4].button("Cancel booking", key=f"cancel_{b.id}"):
                self._run_action(lambda b=b: self._restaurant.cancel_booking(b.id), "Booking cancelled.")

        finished = [b for b in self._restaurant.bookings if b.status(now) == BookingStatus.FINISHED]
        if finished:
            with st.expander(f"Past bookings ({len(finished)})"):
                st.dataframe([{"Guest": b.guest.name, "Phone": b.guest.phone, "Table": b.table.name,
                               "Guests": b.party_size, "Time": str(b.slot)} for b in reversed(finished)], hide_index=True)


class TablesPage(Page):
    """Add, rename, resize and delete tables."""

    title = "Tables"

    def render(self) -> None:
        st.header("Tables")
        with st.form("add_table", clear_on_submit=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            name = c1.text_input("Table name")
            seats = c2.number_input("Seats", 1, 20, 4)
            c3.write("")  # spacer to align the button with the inputs
            submitted = c3.form_submit_button("Add table", type="primary")
        if submitted:
            self._run_action(lambda: self._restaurant.add_table(name, int(seats)),
                             f"Table '{name.strip()}' added.")

        st.subheader("Your tables")
        if not self._restaurant.tables:
            st.info("No tables yet. Add your first table above.")
        for table in self._restaurant.tables:
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            new_name = c1.text_input("Name", table.name, key=f"tname_{table.id}",
                                     label_visibility="collapsed")
            new_seats = c2.number_input("Seats", 1, 20, table.seats, key=f"tseats_{table.id}",
                                        label_visibility="collapsed")
            if c3.button("Save", key=f"save_{table.id}"):
                self._run_action(lambda t=table: self._restaurant.update_table(t.id, new_name, int(new_seats)),
                                 "Table updated.")
            if c4.button("Delete", key=f"del_{table.id}"):
                self._run_action(lambda t=table: self._restaurant.remove_table(t.id),
                                 f"Table '{table.name}' deleted.")


class StatusPage(Page):
    """Read-only overview of every table right now."""

    title = "Status"
    COLUMNS = 3

    def render(self) -> None:
        st.header("Restaurant status")
        now = datetime.now()
        st.caption(f"Updated {now.strftime('%A %d %B, %H:%M:%S')}")
        st.button("Refresh")  # any click reruns the script, which recalculates the status

        totals = self._restaurant.count_by_state(now)
        metrics = st.columns(len(TableState))
        for column, state in zip(metrics, TableState):
            column.metric(state.value, totals[state])

        tables = self._restaurant.tables
        if not tables:
            st.info("There are no tables. Add some on the Tables page.")
            return
        grid = st.columns(self.COLUMNS)
        for index, table in enumerate(tables):
            grid[index % self.COLUMNS].markdown(self._card_html(table, now), unsafe_allow_html=True)

    def _card_html(self, table, now: datetime) -> str:
        """Build the HTML card for one table."""
        state = self._restaurant.table_state(table, now)
        current = self._restaurant.current_booking(table, now)
        upcoming = self._restaurant.next_booking(table, now)

        detail = ""
        if current:
            detail = (f"<div class='detail'>{escape(current.guest.name)} · {current.party_size} guests</div>"
                      f"<div class='detail'>until {current.slot.end.strftime('%H:%M')}</div>")
        muted = "No more bookings"
        if upcoming:
            muted = (f"Next: {escape(upcoming.guest.name)} at "
                     f"{upcoming.slot.start.strftime('%H:%M')}"
                     + ("" if upcoming.slot.start.date() == now.date()
                        else upcoming.slot.start.strftime(" (%d %b)")))
        color = STATE_COLORS[state]
        return (f"<div class='table-card' style='border-left-color:{color}'>"
                f"<div class='name'>{escape(table.name)}</div>"
                f"<div class='seats'>{table.seats} seats</div>"
                f"<div class='state' style='color:{color}'>{state.value}</div>"
                f"{detail}<div class='muted'>{muted}</div></div>")
