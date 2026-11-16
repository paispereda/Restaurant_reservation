import streamlit as st

from pages import BookingsPage, StatusPage, TablesPage
from restaurant import Restaurant
from styles import APP_CSS


def create_demo_restaurant() -> Restaurant:
    """Start with a few tables so the app is not empty on first launch."""
    restaurant = Restaurant("La Mesa")
    for name, seats in [("Window 1", 2), ("Window 2", 2), ("Garden 1", 4),
                        ("Garden 2", 4), ("Family", 6), ("Terrace", 8)]:
        restaurant.add_table(name, seats)
    return restaurant


def main() -> None:
    st.set_page_config(page_title="Restaurant bookings", page_icon="🍽️", layout="wide")
    st.markdown(APP_CSS, unsafe_allow_html=True)

    # session_state keeps the same Restaurant object between reruns (one per browser session)
    if "restaurant" not in st.session_state:
        st.session_state["restaurant"] = create_demo_restaurant()
    restaurant = st.session_state["restaurant"]

    pages = {page.title: page for page in
             (BookingsPage(restaurant), TablesPage(restaurant), StatusPage(restaurant))}

    st.sidebar.title(restaurant.name)
    choice = st.sidebar.radio("Page", list(pages))

    flash = st.session_state.pop("flash", None)  # message left by the previous action
    if flash:
        (st.success if flash[0] == "success" else st.error)(flash[1])

    pages[choice].render()


main()
