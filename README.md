# Restaurant bookings (Streamlit)

    pip install -r requirements.txt
    streamlit run app.py

| File | Responsibility |
|---|---|
| `exceptions.py` | Error hierarchy (`RestaurantError` and subclasses) |
| `models.py` | `Guest`, `TimeSlot`, `Table`, `Booking`, `BookingStatus` (properties, validation) |
| `restaurant.py` | `Restaurant` service: rules, availability, walk-ins, table states |
| `styles.py` | Colours and CSS |
| `pages.py` | `Page` base class + `BookingsPage`, `TablesPage`, `StatusPage` |
| `app.py` | Entry point, sidebar navigation, session state |
