"""Visual theme: colours for table states and the CSS injected into the page."""
from restaurant import TableState

# One colour per table state; used by the status cards and badges.
STATE_COLORS = {
    TableState.FREE: "#2f8f5b",
    TableState.RESERVED_SOON: "#d99a1c",
    TableState.OCCUPIED: "#c2443a",
}

APP_CSS = """
<style>
  h1, h2, h3 { font-family: Georgia, 'Times New Roman', serif; letter-spacing: -0.01em; }
  [data-testid="stSidebar"] { background: #1d4b43; }
  [data-testid="stSidebar"] * { color: #eef5f2 !important; }
  .table-card {
    border-radius: 10px; padding: 16px 18px; margin-bottom: 14px;
    background: #ffffff; border: 1px solid #dfe6e3; border-left-width: 8px;
    min-height: 150px;
  }
  .table-card .name { font-family: Georgia, serif; font-size: 1.35rem; font-weight: 700; }
  .table-card .seats { color: #5d6b66; font-size: 0.9rem; }
  .table-card .state { font-weight: 700; margin-top: 8px; }
  .table-card .detail { color: #33423d; font-size: 0.92rem; margin-top: 2px; }
  .table-card .muted { color: #7b8782; font-size: 0.85rem; margin-top: 6px; }
</style>
"""
