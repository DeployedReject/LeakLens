COLOR_HIGH_RISK = '#EF4444'
COLOR_MED_RISK = '#F59E0B'
COLOR_LOW_RISK = '#10B981'
COLOR_INFO = '#4C9AFF'
COLOR_ACCENT = '#F6821F'
COLOR_ACCENT_BRIGHT = '#FF9B3D'
COLOR_MUTED = '#A3A3A3'
COLOR_CARD_BG = '#141414'
COLOR_BORDER = '#262626'
COLOR_GRID = '#262626'
COLOR_TEXT = '#F5F5F5'
COLOR_TEXT_BODY = '#D4D4D4'
PLOT_TEMPLATE = 'plotly_dark'
PLOT_BG_COLOR = 'rgba(0, 0, 0, 0)'
PAPER_BG_COLOR = 'rgba(0,0,0,0)'

def format_inr(amount, in_lakhs=False):
    if amount is None:
        return '₹0'
    val = float(amount)
    if in_lakhs or abs(val) >= 100000:
        lakhs = val / 100000.0
        return f'₹{lakhs:.2f} Lakh'
    else:
        return f'₹{val:,.0f}'

def format_pct(value, decimals=1):
    if value is None:
        return '0.0%'
    val = float(value)
    if abs(val) <= 1.0 and val != 0:
        val = val * 100.0
    return f'{val:.{decimals}f}%'

def format_int(value):
    if value is None:
        return '0'
    return f'{int(value):,}'

def get_risk_badge(level: str) -> str:
    lvl = str(level).strip().capitalize()
    if 'High' in lvl or 'Critical' in lvl:
        bg = 'rgba(239, 68, 68, 0.15)'
        border = '#EF4444'
        text = '#FCA5A5'
    elif 'Med' in lvl:
        bg = 'rgba(245, 158, 11, 0.15)'
        border = '#F59E0B'
        text = '#FCD34D'
    else:
        bg = 'rgba(16, 185, 129, 0.15)'
        border = '#10B981'
        text = '#6EE7B7'
    style = f'background-color: {bg}; border: 1px solid {border}; color: {text}; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.03em; text-transform: uppercase; display: inline-block;'
    return f'<span style="{style}">{level}</span>'
