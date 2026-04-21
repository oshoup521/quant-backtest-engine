"""
Theme System
-------------
Single source of truth for all colors used across the app.
Two palettes: 'dark' (GitHub Dark) and 'light' (GitHub Light).
Switch via st.session_state["theme_mode"].
"""

import streamlit as st

DEFAULT_MODE: str = "dark"

# ---------------------------------------------------------------------------
# Palette definitions
# ---------------------------------------------------------------------------
# Each theme exposes the same keys so consumers can swap palettes blindly.

DARK: dict[str, str] = {
    # Surfaces
    "bg":           "#0d1117",   # page background
    "panel":        "#161b22",   # cards, sidebar
    "panel_hover":  "#1f242c",
    "border":       "#21262d",
    "border_strong": "#30363d",

    # Text
    "text":         "#e6edf3",
    "text_muted":   "#8b949e",
    "text_dim":     "#6e7681",

    # Accents
    "accent":       "#1f6feb",   # primary (selected tab, focus)
    "accent_strong": "#388bfd",
    "link":         "#58a6ff",

    # Status
    "success":      "#26a641",
    "success_soft": "rgba(38, 166, 65, 0.08)",
    "danger":       "#f85149",
    "danger_soft":  "rgba(248, 81, 73, 0.08)",
    "warning":      "#d29922",
    "warning_soft": "rgba(210, 153, 34, 0.08)",

    # Brand colors used in pills / chart overlays
    "orange":       "#ffa657",
    "purple":       "#d2a8ff",
    "cyan":         "#79c0ff",
    "neutral_soft": "rgba(139, 148, 158, 0.08)",

    # Buttons
    "btn_primary_bg":   "#238636",
    "btn_primary_hover": "#2ea043",
    "btn_secondary_bg": "#21262d",
    "btn_secondary_hover": "#30363d",

    # Plotly-specific
    "grid":         "#21262d",
    "candle_up":    "#26a641",
    "candle_down":  "#f85149",
    "volume_up":    "rgba(38, 166, 65, 0.45)",
    "volume_down":  "rgba(248, 81, 73, 0.45)",
}

LIGHT: dict[str, str] = {
    # Surfaces — GitHub Light
    "bg":           "#ffffff",
    "panel":        "#f6f8fa",
    "panel_hover":  "#eaeef2",
    "border":       "#d0d7de",
    "border_strong": "#afb8c1",

    # Text
    "text":         "#1f2328",
    "text_muted":   "#656d76",
    "text_dim":     "#8c959f",

    # Accents
    "accent":       "#0969da",
    "accent_strong": "#0550ae",
    "link":         "#0969da",

    # Status — slightly deeper than dark variants for readability on white
    "success":      "#1a7f37",
    "success_soft": "rgba(26, 127, 55, 0.08)",
    "danger":       "#cf222e",
    "danger_soft":  "rgba(207, 34, 46, 0.08)",
    "warning":      "#9a6700",
    "warning_soft": "rgba(154, 103, 0, 0.10)",

    "orange":       "#bc4c00",
    "purple":       "#8250df",
    "cyan":         "#0969da",
    "neutral_soft": "rgba(101, 109, 118, 0.08)",

    "btn_primary_bg":   "#1f883d",
    "btn_primary_hover": "#1a7f37",
    "btn_secondary_bg": "#f6f8fa",
    "btn_secondary_hover": "#eaeef2",

    "grid":         "#d0d7de",
    "candle_up":    "#1a7f37",
    "candle_down":  "#cf222e",
    "volume_up":    "rgba(26, 127, 55, 0.45)",
    "volume_down":  "rgba(207, 34, 46, 0.45)",
}

THEMES: dict[str, dict[str, str]] = {"dark": DARK, "light": LIGHT}


def get_theme() -> dict[str, str]:
    """Return the active theme dict (defaults to dark on first run)."""
    mode = st.session_state.get("theme_mode", DEFAULT_MODE)
    return THEMES.get(mode, DARK)


def get_plotly_template() -> str:
    """Plotly template name appropriate for the active theme."""
    return "plotly_dark" if st.session_state.get("theme_mode", DEFAULT_MODE) == "dark" else "plotly_white"
