"""Modal screens: help, trade form, and spot entry form."""
from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Select, Static

import trades

HELP_TEXT = """\
[bold cyan]Keyboard shortcuts[/bold cyan]

  [bold]1[/bold]          Dashboard
  [bold]2[/bold]          Trades
  [bold]3[/bold]          Spot
  [bold]A[/bold]          Add trade
  [bold]S[/bold]          Add spot entry
  [bold]D[/bold]          Delete selected row
  [bold]R[/bold]          Refresh BTC price
  [bold]?[/bold]          This help
  [bold]Q[/bold]          Quit

[dim]— Forms —[/dim]
  [bold]Ctrl+S[/bold]     Save
  [bold]Escape[/bold]     Cancel / close

[dim]— Table —[/dim]
  [bold]↑ ↓[/bold]        Navigate rows
  [bold]PgUp PgDn[/bold]  Jump pages

[dim]Press Escape to close[/dim]"""

_HINT = "[dim]  Ctrl+S[/dim] [white]save[/white]   [dim]Esc[/dim] [white]cancel[/white]"


class HelpModal(ModalScreen):
    DEFAULT_CSS = """
    HelpModal { align: center middle; }
    HelpModal > Static {
        width: 52;
        height: auto;
        border: thick $accent 60%;
        background: $surface 60%;
        padding: 1 2;
    }
    """
    BINDINGS = [("escape", "dismiss", "Close"), ("question_mark", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        yield Static(HELP_TEXT)


class AddTradeModal(ModalScreen):
    DEFAULT_CSS = """
    AddTradeModal { align: center middle; }
    AddTradeModal > Vertical {
        width: 64;
        height: 90%;
        border: thick $accent 60%;
        background: $surface 60%;
        padding: 0;
    }
    AddTradeModal #hint  { background: $panel 60%; padding: 0 2; height: 1; color: $text-muted; }
    AddTradeModal #title { text-align: center; margin: 1 0; color: $text; }
    AddTradeModal Label  { margin-top: 1; color: $text-muted; }
    AddTradeModal VerticalScroll { padding: 0 2 1 2; background: transparent; height: 1fr; }
    """
    BINDINGS = [
        ("ctrl+s", "save",   "Save"),
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with Vertical():
            yield Static(_HINT, id="hint")
            with VerticalScroll():
                yield Label("[bold]New Trade[/bold]", id="title")
                yield Label("Direction")
                yield Select([("Long ↑", "Long"), ("Short ↓", "Short")],
                             id="f-direction", value="Long")
                yield Label("Status")
                yield Select([("Filled ✅", "Filled"), ("Canceled ❌", "Canceled"),
                              ("Open 🔄", "Open")], id="f-status", value="Filled")
                yield Label("P&L (sats — negative if loss)")
                yield Input(id="f-pnl",          placeholder="0")
                yield Label("Quantity (USD — contract value)")
                yield Input(id="f-quantity",     placeholder="500.00")
                yield Label("Margin (sats)")
                yield Input(id="f-margin",       placeholder="204257")
                yield Label("Leverage")
                yield Input(id="f-leverage",     placeholder="15.0")
                yield Label("Entry price (USD)")
                yield Input(id="f-price",        placeholder="67300")
                yield Label("Close event")
                yield Select(
                    [("— None / Manual",  "none"),
                     ("Liquidation 💀",   "liquidation"),
                     ("Stop Loss 🛑",     "stoploss"),
                     ("Take Profit ✅",   "takeprofit")],
                    id="f-close-event", value="none")
                yield Label("Trading fees (sats)")
                yield Input(id="f-fees",         placeholder="0")
                yield Label("Funding cost (sats)")
                yield Input(id="f-funding",      placeholder="0")
                yield Label("Creation date (YYYY-MM-DD HH:MM)")
                yield Input(value=now,            id="f-created")
                yield Label("Filled date (leave empty if not applicable)")
                yield Input(id="f-filled",       placeholder="2026-02-08 22:10")
                yield Label("External ID (optional)")
                yield Input(id="f-id",           placeholder="e0ad7f33-c690...")
                yield Label("Notes")
                yield Input(id="f-notes",        placeholder="Strategy, context...")

    def _str(self, id_: str) -> str:
        return self.query_one(id_, Input).value.strip()

    def _int(self, id_: str) -> int:
        try: return int(self._str(id_) or "0")
        except ValueError: return 0

    def _float(self, id_: str) -> float:
        try: return float(self._str(id_) or "0")
        except ValueError: return 0.0

    def action_save(self) -> None:
        direction = self.query_one("#f-direction", Select).value
        status    = self.query_one("#f-status",    Select).value
        created   = self._str("#f-created")

        if direction is Select.BLANK or status is Select.BLANK or not created:
            self.notify("Direction, status and date are required.", severity="error")
            return
        try:
            datetime.strptime(created, "%Y-%m-%d %H:%M")
        except ValueError:
            self.notify("Invalid date. Format: YYYY-MM-DD HH:MM", severity="error")
            return

        self.dismiss(trades.add_trade({
            "id":            self._str("#f-id"),
            "direction":     direction,
            "status":        status,
            "pnl":           self._int("#f-pnl"),
            "quantity":      self._float("#f-quantity"),
            "margin":        self._int("#f-margin"),
            "leverage":      self._float("#f-leverage"),
            "price":         self._float("#f-price"),
            "close_event":   self.query_one("#f-close-event", Select).value or "none",
            "trading_fees":  self._int("#f-fees"),
            "funding_cost":  self._int("#f-funding"),
            "creation_date": created,
            "filled_date":   self._str("#f-filled"),
            "notes":         self._str("#f-notes"),
        }))

    def action_cancel(self) -> None:
        self.dismiss(None)


class AddSpotModal(ModalScreen):
    DEFAULT_CSS = """
    AddSpotModal { align: center middle; }
    AddSpotModal > Vertical {
        width: 56;
        height: auto;
        border: thick $accent 60%;
        background: $surface 60%;
        padding: 0;
    }
    AddSpotModal #hint  { background: $panel 60%; padding: 0 2; height: 1; color: $text-muted; }
    AddSpotModal #title { text-align: center; margin: 1 0; color: $text; }
    AddSpotModal Label  { margin-top: 1; color: $text-muted; }
    AddSpotModal ScrollableContainer { padding: 0 2 1 2; background: transparent; height: auto; }
    """
    BINDINGS = [
        ("ctrl+s", "save",   "Save"),
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        today = datetime.now().strftime("%Y-%m-%d")
        with Vertical():
            yield Static(_HINT, id="hint")
            with ScrollableContainer():
                yield Label("[bold]Add Spot Entry[/bold]", id="title")
                yield Label("Sats  [dim](+ deposit / – withdrawal)[/dim]")
                yield Input(id="s-sats",  placeholder="100000")
                yield Label("Date (YYYY-MM-DD)")
                yield Input(value=today,  id="s-date")
                yield Label("Notes")
                yield Input(id="s-notes", placeholder="Profit withdrawal, OTC buy...")

    def action_save(self) -> None:
        sats_str = self.query_one("#s-sats",  Input).value.strip()
        date_str = self.query_one("#s-date",  Input).value.strip()
        notes    = self.query_one("#s-notes", Input).value.strip()
        try:
            sats = int(sats_str)
            datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            self.notify("Sats must be an integer and date must be YYYY-MM-DD.", severity="error")
            return
        self.dismiss(trades.add_spot_entry(date_str, sats, notes))

    def action_cancel(self) -> None:
        self.dismiss(None)
