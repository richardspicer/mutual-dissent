"""Shared layout components for the Mutual Dissent web interface.

Provides the navigation shell (header + left drawer) used by all pages.
Dark mode is set globally via ui.run(dark=True) in app.py.
"""

from __future__ import annotations

from nicegui import ui

from mutual_dissent import __version__


def create_layout() -> None:
    """Create the shared navigation shell.

    Adds a header with the app title, a left drawer with page navigation
    links, and a footer with the phase string. Call this at the top of
    every @ui.page function.
    """
    with ui.header().classes(
        "bg-zinc-950/70 backdrop-blur-md border-b border-zinc-800 "
        "items-center justify-between px-6 py-4"
    ):
        with ui.row().classes("items-center gap-4"):
            ui.icon("forum", color="emerald-400").classes("text-4xl")
            ui.label("Mutual Dissent").classes("text-2xl font-bold tracking-tighter text-zinc-100")
        ui.label(f"v{__version__}").classes("text-xs text-zinc-500 font-mono")

    with ui.left_drawer(top_corner=True, bottom_corner=True).classes(
        "bg-zinc-900 border-r border-zinc-800 text-zinc-100 w-64"
    ):
        ui.label("Navigation").classes(
            "mx-6 mt-8 mb-3 text-xs uppercase tracking-widest text-zinc-400 font-medium"
        )
        for label, target, icon in [
            ("Live Debate", "/", "play_arrow"),
            ("Dashboard", "/dashboard", "dashboard"),
            ("Config", "/config", "settings"),
        ]:
            with ui.row().classes(
                "mx-6 items-center gap-3 py-3 hover:bg-zinc-800 rounded-xl cursor-pointer"
            ):
                ui.icon(icon, color="zinc-400").classes("text-xl")
                ui.link(label, target).classes("text-zinc-200 no-underline font-medium flex-1")

    with ui.footer().classes(
        "bg-zinc-950 border-t border-zinc-800 text-zinc-500 text-xs py-3 px-6"
    ):
        ui.label("Cross-vendor AI debate engine").classes("font-mono")
