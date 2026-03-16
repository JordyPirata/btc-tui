"""Pantallas modales: ayuda, formulario de trade y formulario de spot."""
from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Select, Static

import trades

HELP_TEXT = """\
[bold cyan]Atajos de teclado[/bold cyan]

  [bold]1[/bold]          Dashboard
  [bold]2[/bold]          Trades
  [bold]3[/bold]          Spot
  [bold]A[/bold]          Agregar trade
  [bold]S[/bold]          Agregar entrada spot
  [bold]D[/bold]          Eliminar fila seleccionada
  [bold]R[/bold]          Actualizar precio BTC
  [bold]?[/bold]          Esta ayuda
  [bold]Q[/bold]          Salir

[dim]— Formularios —[/dim]
  [bold]Ctrl+S[/bold]     Guardar
  [bold]Escape[/bold]     Cancelar / cerrar

[dim]— Tabla —[/dim]
  [bold]↑ ↓[/bold]        Navegar filas
  [bold]PgUp PgDn[/bold]  Saltar páginas

[dim]Presiona Escape para cerrar[/dim]"""

_HINT = "[dim]  Ctrl+S[/dim] [white]guardar[/white]   [dim]Esc[/dim] [white]cancelar[/white]"


class HelpModal(ModalScreen):
    DEFAULT_CSS = """
    HelpModal { align: center middle; }
    HelpModal > Static {
        width: 52;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    """
    BINDINGS = [("escape", "dismiss", "Cerrar"), ("question_mark", "dismiss", "Cerrar")]

    def compose(self) -> ComposeResult:
        yield Static(HELP_TEXT)


class AddTradeModal(ModalScreen):
    DEFAULT_CSS = """
    AddTradeModal { align: center middle; }
    AddTradeModal > Vertical {
        width: 64;
        height: 90%;
        border: thick $accent;
        background: $surface;
        padding: 0;
    }
    AddTradeModal #hint      { background: $panel; padding: 0 2; height: 1; color: $text-muted; }
    AddTradeModal #title     { text-align: center; margin: 1 0; color: $text; }
    AddTradeModal Label      { margin-top: 1; color: $text-muted; }
    AddTradeModal ScrollableContainer { padding: 0 2 1 2; background: transparent; }
    """
    BINDINGS = [
        ("ctrl+s", "save",   "Guardar"),
        ("escape", "cancel", "Cancelar"),
    ]

    def compose(self) -> ComposeResult:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with Vertical():
            yield Static(_HINT, id="hint")
            with ScrollableContainer():
                yield Label("[bold]Nuevo Trade[/bold]", id="title")
                yield Label("Dirección")
                yield Select([("Long ↑", "Long"), ("Short ↓", "Short")],
                             id="f-direction", value="Long")
                yield Label("Estado")
                yield Select([("Filled ✅", "Filled"), ("Canceled ❌", "Canceled"),
                              ("Open 🔄", "Open")], id="f-status", value="Filled")
                yield Label("P&L (sats — negativo si fue pérdida)")
                yield Input(id="f-pnl",          placeholder="0")
                yield Label("Quantity (sats)")
                yield Input(id="f-quantity",     placeholder="2000")
                yield Label("Trade Margin (sats)")
                yield Input(id="f-trade-margin", placeholder="198117")
                yield Label("Margin (sats)")
                yield Input(id="f-margin",       placeholder="204257")
                yield Label("Leverage")
                yield Input(id="f-leverage",     placeholder="15.0")
                yield Label("Precio entrada (USD)")
                yield Input(id="f-price",        placeholder="67300")
                yield Label("Liquidación (USD)")
                yield Input(id="f-liquidation",  placeholder="63094")
                yield Label("Stoploss (USD)")
                yield Input(id="f-sl",           placeholder="66627")
                yield Label("Takeprofit (USD)")
                yield Input(id="f-tp",           placeholder="126000")
                yield Label("Trading fees (sats)")
                yield Input(id="f-fees",         placeholder="0")
                yield Label("Funding cost (sats)")
                yield Input(id="f-funding",      placeholder="0")
                yield Label("Fecha creación (YYYY-MM-DD HH:MM)")
                yield Input(value=now,            id="f-created")
                yield Label("Fecha filled (vacío si no aplica)")
                yield Input(id="f-filled",       placeholder="2026-02-08 22:10")
                yield Label("ID externo (opcional)")
                yield Input(id="f-id",           placeholder="e0ad7f33-c690...")
                yield Label("Notas")
                yield Input(id="f-notes",        placeholder="Estrategia, contexto...")

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
            self.notify("Dirección, estado y fecha son obligatorios.", severity="error")
            return
        try:
            datetime.strptime(created, "%Y-%m-%d %H:%M")
        except ValueError:
            self.notify("Fecha inválida. Formato: YYYY-MM-DD HH:MM", severity="error")
            return

        self.dismiss(trades.add_trade({
            "id":            self._str("#f-id"),
            "direction":     direction,
            "status":        status,
            "pnl":           self._int("#f-pnl"),
            "quantity":      self._int("#f-quantity"),
            "trade_margin":  self._int("#f-trade-margin"),
            "margin":        self._int("#f-margin"),
            "leverage":      self._float("#f-leverage"),
            "price":         self._float("#f-price"),
            "liquidation":   self._float("#f-liquidation"),
            "stoploss":      self._float("#f-sl"),
            "takeprofit":    self._float("#f-tp"),
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
        border: thick $accent;
        background: $surface;
        padding: 0;
    }
    AddSpotModal #hint  { background: $panel; padding: 0 2; height: 1; color: $text-muted; }
    AddSpotModal #title { text-align: center; margin: 1 0; color: $text; }
    AddSpotModal Label  { margin-top: 1; color: $text-muted; }
    AddSpotModal ScrollableContainer { padding: 0 2 1 2; background: transparent; height: auto; }
    """
    BINDINGS = [
        ("ctrl+s", "save",   "Guardar"),
        ("escape", "cancel", "Cancelar"),
    ]

    def compose(self) -> ComposeResult:
        today = datetime.now().strftime("%Y-%m-%d")
        with Vertical():
            yield Static(_HINT, id="hint")
            with ScrollableContainer():
                yield Label("[bold]Agregar Spot[/bold]", id="title")
                yield Label("Sats  [dim](+ ingreso / – retiro)[/dim]")
                yield Input(id="s-sats",  placeholder="100000")
                yield Label("Fecha (YYYY-MM-DD)")
                yield Input(value=today,  id="s-date")
                yield Label("Notas")
                yield Input(id="s-notes", placeholder="Retiro de profits, compra OTC...")

    def action_save(self) -> None:
        sats_str = self.query_one("#s-sats",  Input).value.strip()
        date_str = self.query_one("#s-date",  Input).value.strip()
        notes    = self.query_one("#s-notes", Input).value.strip()
        try:
            sats = int(sats_str)
            datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            self.notify("Sats debe ser entero y fecha YYYY-MM-DD.", severity="error")
            return
        self.dismiss(trades.add_spot_entry(date_str, sats, notes))

    def action_cancel(self) -> None:
        self.dismiss(None)
