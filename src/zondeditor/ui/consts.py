from __future__ import annotations

APP_TITLE = "ZondEditor SZ"
APP_VERSION = "dev"
DEFAULT_GEO_KIND = "K2"

GUI_RED = "#ff3b30"
GUI_ORANGE = "#ff9500"
GUI_YELLOW = "#ffd60a"
GUI_BLUE = "#007aff"
GUI_PURPLE = "#af52de"
GUI_GREEN = "#34c759"
GUI_GRAY = "#8e8e93"

# ---- extra UI colors used by table/header ----
GUI_HDR_OFF = "#f2f2f2"    # header background (export OFF)
GUI_HDR_ON = "#dbeafe"     # header background (export ON / active)
GUI_HDR = GUI_HDR_ON       # legacy alias (kept)

GUI_HDR_TXT = "#111111"    # header text
GUI_CELL_BG = "#ffffff"    # cell background
GUI_GRID = "#d0d0d0"       # grid lines\n\n# ---- UI icon glyphs (fallbacks) ----
# If Segoe MDL2 Assets is available, these render as icons; otherwise show readable symbols.
ICON_CALENDAR = "\uE787"  # MDL2 Calendar
ICON_CLOCK = "🕒"
ICON_CHECK = "✓"
ICON_CROSS = "✕"
ICON_WARN = "⚠"
ICON_INFO = "ℹ"
ICON_EDIT = "✎"
ICON_TRASH = "\uE74D"  # MDL2 Delete
# -----------------------------------\n

# ---- UI icon glyphs (fallbacks) ----
# If Segoe MDL2 Assets is available, these render as icons; otherwise show readable symbols.
ICON_COPY = "\uE8C8"  # MDL2 Copy
ICON_PASTE = "\uE77F"  # MDL2 Paste
ICON_UNDO = "↶"
ICON_REDO = "↷"
ICON_PLUS = "+"
ICON_MINUS = "−"
ICON_SAVE = "💾"
ICON_OPEN = "📂"
ICON_EXPORT = "⤓"
ICON_IMPORT = "⤒"
ICON_SETTINGS = "⚙"
ICON_SEARCH = "🔍"
ICON_REFRESH = "⟳"
# -----------------------------------

ICON_DELETE = ICON_TRASH

# ---- extra depth column colors ----
GUI_DEPTH_BG = "#f7f7f7"   # depth column background
GUI_DEPTH_TXT = "#111111"  # depth text
GUI_ORANGE_P = GUI_ORANGE  # preview mode color
GUI_BLUE_P = GUI_BLUE  # preview mode color

# ---- graph overlay colors (separate from table highlight palette) ----
GRAPH_QC_GREEN = "#16a34a"
GRAPH_FS_BLUE = "#2563eb"

GRAPH_RF_ORANGE = "#f59e0b"
