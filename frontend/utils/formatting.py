"""
Formatting utilities and design constants for LeakLens.
"""

# Brand & Status Color Palette
COLOR_HIGH_RISK = "#EF4444"    # Crimson Red
COLOR_MED_RISK = "#F59E0B"     # Amber Orange
COLOR_LOW_RISK = "#10B981"     # Emerald Green
COLOR_INFO = "#4C9AFF"         # Neutral Blue
COLOR_ACCENT = "#F6821F"       # Cloudflare Orange
COLOR_ACCENT_BRIGHT = "#FF9B3D"
COLOR_MUTED = "#A3A3A3"        # Neutral Muted
COLOR_CARD_BG = "#141414"      # Near-black Card
COLOR_BORDER = "#262626"       # Subdued Border
COLOR_GRID = "#262626"         # Chart Gridline
COLOR_TEXT = "#F5F5F5"         # Primary Text
COLOR_TEXT_BODY = "#D4D4D4"    # Body Copy

# Plotly theme styling helper
PLOT_TEMPLATE = "plotly_dark"
PLOT_BG_COLOR = "rgba(0, 0, 0, 0)"
PAPER_BG_COLOR = "rgba(0,0,0,0)"

def format_inr(amount, in_lakhs=False):
    """
    Format numeric values to Indian Rupee notation.
    Example: 1622000 -> ₹16.22 Lakh or ₹16,22,000
    """
    if amount is None:
        return "₹0"
    
    val = float(amount)
    if in_lakhs or abs(val) >= 100000:
        lakhs = val / 100000.0
        return f"₹{lakhs:.2f} Lakh"
    else:
        # Standard Indian comma grouping or simple thousands
        return f"₹{val:,.0f}"

def format_pct(value, decimals=1):
    """Format decimal or percentage to string."""
    if value is None:
        return "0.0%"
    # If passed as 0.379 vs 37.9
    val = float(value)
    if abs(val) <= 1.0 and val != 0:
        val = val * 100.0
    return f"{val:.{decimals}f}%"

def format_int(value):
    """Format integer with thousands separator."""
    if value is None:
        return "0"
    return f"{int(value):,}"

def get_risk_badge(level: str) -> str:
    """Return styled HTML badge for risk levels."""
    lvl = str(level).strip().capitalize()
    if "High" in lvl or "Critical" in lvl:
        bg = "rgba(239, 68, 68, 0.15)"
        border = "#EF4444"
        text = "#FCA5A5"
    elif "Med" in lvl:
        bg = "rgba(245, 158, 11, 0.15)"
        border = "#F59E0B"
        text = "#FCD34D"
    else:
        bg = "rgba(16, 185, 129, 0.15)"
        border = "#10B981"
        text = "#6EE7B7"

    # Keep the badge on a single line: multi-line fragments nested into other
    # markdown blocks can break HTML-block detection in Streamlit.
    style = (
        f"background-color: {bg}; border: 1px solid {border}; color: {text}; "
        "padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; "
        "font-weight: 600; letter-spacing: 0.03em; text-transform: uppercase; "
        "display: inline-block;"
    )
    return f'<span style="{style}">{level}</span>'
