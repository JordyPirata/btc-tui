"""BTC Futures TUI — P&L en sats, spot acumulado en USD."""
from __future__ import annotations

from datetime import datetime

import plotext as plt
import requests
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

import trades as tr

BTC_PRICE_URL = (
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
)

HELP_TEXT = """\
[bold cyan]Atajos de teclado[/bold cyan]

  [bold]1[/bold]          Dashboard
  [bold]2[/bold]          Trades
  [bold]A[/bold]          Agregar trade
  [bold]D[/bold]          Eliminar trade seleccionado
  [bold]R[/bold]          Actualizar precio BTC
  [bold]?[/bold]          Esta ayuda
  [bold]Q[/bold]          Salir

[dim]— Formulario de trade —[/dim]
  [bold]Ctrl+S[/bold]     Guardar
  [bold]Escape[/bold]     Cancelar / cerrar

[dim]— Tabla —[/dim]
  [bold]↑ ↓[/bold]        Navegar filas
  [bold]PgUp PgDn[/bold]  Saltar páginas

[dim]Presiona Escape para cerrar[/dim]"""


def fetch_btc_price() -> float:
    try:
        r = requests.get(BTC_PRICE_URL, timeout=6)
        return float(r.json()["bitcoin"]["usd"])
    except Exception:
        return 0.0


def fmt_sats(n: int, sign: bool = True) -> str:
    s = "+" if (sign and n > 0) else ""
    return f"{s}{n:,}"


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------


class PlotWidget(Static):
    DEFAULT_CSS = """
    PlotWidget {
        width: 1fr;
        height: 100%;
        border: solid $panel-darken-2;
        background: transparent;
    }
    """

    def __init__(self, title: str = "", **kwargs) -> None:
        super().__init__("", markup=False, **kwargs)
        self._title = title
        self._dates: list[str] = []
        self._values: list[float] = []
        self._bar_mode = False

    def on_mount(self) -> None:
        self._redraw()

    def on_resize(self) -> None:
        self._redraw()

    def update_line(self, dates: list[str], values: list[float]) -> None:
        self._dates, self._values, self._bar_mode = dates, values, False
        self._redraw()

    def update_bars(self, dates: list[str], values: list[float]) -> None:
        self._dates, self._values, self._bar_mode = dates, values, True
        self._redraw()

    def _redraw(self) -> None:
        w = max(self.size.width - 2, 10)
        h = max(self.size.height - 2, 5)
        plt.clf()
        plt.plotsize(w, h)
        plt.title(self._title)
        plt.theme("dark")

        if self._dates and self._values:
            x = list(range(len(self._dates)))
            if self._bar_mode:
                plt.bar(x, self._values,
                        color=["green" if v >= 0 else "red" for v in self._values])
            else:
                plt.plot(x, self._values, marker="braille")
                plt.hline(0, "white")
            step = max(1, len(x) // 6)
            plt.xticks(x[::step], [self._dates[i] for i in x[::step]])
        else:
            plt.text("Sin datos  —  [A] para agregar tu primer trade", x=1, y=1)

        self.update(Text.from_ansi(plt.build()))


# ---------------------------------------------------------------------------
# Modales
# ---------------------------------------------------------------------------


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
    AddTradeModal #modal-hint {
        background: $panel;
        padding: 0 2;
        color: $text-muted;
        height: 1;
    }
    AddTradeModal ScrollableContainer {
        padding: 0 2 1 2;
        background: transparent;
    }
    AddTradeModal Label {
        margin-top: 1;
        color: $text-muted;
    }
    AddTradeModal #modal-title {
        text-align: center;
        margin: 1 0;
        color: $text;
    }
    """
    BINDINGS = [
        ("ctrl+s", "save_trade", "Guardar"),
        ("escape", "cancel_modal", "Cancelar"),
    ]

    def compose(self) -> ComposeResult:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with Vertical():
            yield Static(
                "[dim]  Ctrl+S[/dim] [white]guardar[/white]"
                "   [dim]Esc[/dim] [white]cancelar[/white]",
                id="modal-hint",
            )
            with ScrollableContainer():
                yield Label("[bold]Nuevo Trade[/bold]", id="modal-title")

                yield Label("Dirección")
                yield Select([("Long ↑", "Long"), ("Short ↓", "Short")],
                             id="f-direction", value="Long")

                yield Label("Estado")
                yield Select(
                    [("Filled ✅", "Filled"), ("Canceled ❌", "Canceled"), ("Open 🔄", "Open")],
                    id="f-status", value="Filled",
                )

                yield Label("P&L (sats — negativo si fue pérdida)")
                yield Input(id="f-pnl", placeholder="0")

                yield Label("Quantity (sats)")
                yield Input(id="f-quantity", placeholder="2000")

                yield Label("Trade Margin (sats)")
                yield Input(id="f-trade-margin", placeholder="198117")

                yield Label("Margin (sats)")
                yield Input(id="f-margin", placeholder="204257")

                yield Label("Leverage")
                yield Input(id="f-leverage", placeholder="15.0")

                yield Label("Precio entrada (USD)")
                yield Input(id="f-price", placeholder="67300")

                yield Label("Liquidación (USD)")
                yield Input(id="f-liquidation", placeholder="63094")

                yield Label("Stoploss (USD)")
                yield Input(id="f-sl", placeholder="66627")

                yield Label("Takeprofit (USD)")
                yield Input(id="f-tp", placeholder="126000")

                yield Label("Trading fees (sats)")
                yield Input(id="f-fees", placeholder="0")

                yield Label("Funding cost (sats)")
                yield Input(id="f-funding", placeholder="0")

                yield Label("Fecha creación (YYYY-MM-DD HH:MM)")
                yield Input(value=now, id="f-created")

                yield Label("Fecha filled (vacío si no aplica)")
                yield Input(id="f-filled", placeholder="2026-02-08 22:10")

                yield Label("ID externo (opcional)")
                yield Input(id="f-id", placeholder="e0ad7f33-c690...")

                yield Label("Notas")
                yield Input(id="f-notes", placeholder="Estrategia, contexto...")

    def _get(self, id_: str, default: str = "") -> str:
        return self.query_one(id_, Input).value.strip() or default

    def _int(self, id_: str) -> int:
        try:
            return int(self._get(id_, "0"))
        except ValueError:
            return 0

    def _float(self, id_: str) -> float:
        try:
            return float(self._get(id_, "0"))
        except ValueError:
            return 0.0

    def action_save_trade(self) -> None:
        direction = self.query_one("#f-direction", Select).value
        status = self.query_one("#f-status", Select).value
        created = self._get("#f-created")

        if direction is Select.BLANK or status is Select.BLANK or not created:
            self.notify("Dirección, estado y fecha son obligatorios.", severity="error")
            return
        try:
            datetime.strptime(created, "%Y-%m-%d %H:%M")
        except ValueError:
            self.notify("Fecha inválida. Formato: YYYY-MM-DD HH:MM", severity="error")
            return

        trade = tr.add_trade({
            "id":           self._get("#f-id"),
            "direction":    direction,
            "status":       status,
            "pnl":          self._int("#f-pnl"),
            "quantity":     self._int("#f-quantity"),
            "trade_margin": self._int("#f-trade-margin"),
            "margin":       self._int("#f-margin"),
            "leverage":     self._float("#f-leverage"),
            "price":        self._float("#f-price"),
            "liquidation":  self._float("#f-liquidation"),
            "stoploss":     self._float("#f-sl"),
            "takeprofit":   self._float("#f-tp"),
            "trading_fees": self._int("#f-fees"),
            "funding_cost": self._int("#f-funding"),
            "creation_date": created,
            "filled_date":  self._get("#f-filled"),
            "notes":        self._get("#f-notes"),
        })
        self.dismiss(trade)

    def action_cancel_modal(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# App principal
# ---------------------------------------------------------------------------


class BtcTuiApp(App):
    CSS = """
    /* ── Global ───────────────────────────────────────── */
    Screen { background: $background; }

    TabbedContent { background: transparent; }
    TabbedContent > TabPane { background: transparent; padding: 0; }
    ContentSwitcher { background: transparent; }

    /* ── Stats bar (dashboard) ─────────────────────────── */
    #stats-bar {
        height: 1;
        background: $panel;
        padding: 0 1;
        color: $text;
    }

    /* ── Charts ────────────────────────────────────────── */
    #charts-row { height: 1fr; }

    /* ── Trades tab ────────────────────────────────────── */
    #trade-status {
        height: 1;
        background: $panel;
        padding: 0 1;
        color: $text-muted;
    }

    DataTable {
        height: 1fr;
        background: transparent;
    }
    """

    BINDINGS = [
        ("1",           "goto_dashboard",   "Dashboard"),
        ("2",           "goto_trades",      "Trades"),
        ("a",           "add_trade",        "Agregar"),
        ("d",           "delete_trade",     "Eliminar"),
        ("r",           "refresh_data",     "Actualizar"),
        ("question_mark", "show_help",      "Ayuda"),
        ("q",           "quit",             "Salir"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._current_price = 0.0
        self._trades: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("Dashboard", id="tab-dashboard"):
                yield Static("", id="stats-bar")
                with Horizontal(id="charts-row"):
                    yield PlotWidget("P&L Acumulado (sats)", id="chart-cumulative")
                    yield PlotWidget("P&L por Trade (sats)", id="chart-bars")
            with TabPane("Trades", id="tab-trades"):
                yield Static("", id="trade-status")
                yield DataTable(id="trades-table", zebra_stripes=True, cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "BTC Futures"
        table = self.query_one("#trades-table", DataTable)
        table.add_columns(
            "ID", "Dir", "Estado", "P&L (sats)", "Fees",
            "Margin", "Lev", "Entrada", "Liq.", "Fecha", "Notas",
        )
        self.action_refresh_data()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def action_refresh_data(self) -> None:
        self._fetch()

    @work(thread=True)
    def _fetch(self) -> None:
        price = fetch_btc_price()
        self.call_from_thread(self._update_ui, price)

    def _update_ui(self, price: float) -> None:
        self._current_price = price
        self._trades = tr.load_trades()
        s = tr.compute_stats(self._trades, price)
        self.sub_title = (
            f"BTC ${price:,.0f}"
            f"  │  Spot {'+'if s['spot_usd']>=0 else ''}${s['spot_usd']:,.2f} USD"
        )
        self._refresh_stats_bar(s)
        self._refresh_trade_status(s, price)
        self._refresh_table()
        self._refresh_charts()

    def _refresh_stats_bar(self, s: dict) -> None:
        pnl_c  = "green" if s["net_pnl"] >= 0 else "red"
        spot_c = "green" if s["spot_usd"] >= 0 else "red"
        wr_c   = "green" if s["win_rate"] >= 50 else "red"

        self.query_one("#stats-bar", Static).update(
            f"P&L [{pnl_c}]{fmt_sats(s['net_pnl'])} sats[/{pnl_c}]"
            f"   Fees [yellow]{s['total_fees']:,}[/yellow]"
            f"   Win [{wr_c}]{s['win_rate']:.0f}%[/{wr_c}]"
            f" [dim]({s['winners']}W·{s['losers']}L)[/dim]"
            f"   Mejor [green]{fmt_sats(s['best'])}[/green]"
            f"   Peor [red]{fmt_sats(s['worst'])}[/red]"
            f"   Spot [{spot_c}]${s['spot_usd']:,.2f} USD[/{spot_c}]"
        )

    def _refresh_trade_status(self, s: dict, price: float) -> None:
        price_str = f"${price:,.0f}" if price else "offline"
        self.query_one("#trade-status", Static).update(
            f"BTC [cyan]{price_str}[/cyan]"
            f"   [white]{s['filled']}[/white] filled"
            f" · [dim]{s['canceled']} canceled[/dim]"
            f"   [dim]↑↓ navegar  ·  A agregar  ·  D eliminar[/dim]"
        )

    def _refresh_table(self) -> None:
        table = self.query_one("#trades-table", DataTable)
        table.clear()
        for t in reversed(self._trades):
            dir_m = "[green]Long ↑[/green]" if t["direction"] == "Long" else "[red]Short ↓[/red]"
            st_m = {"Filled": "[green]Filled[/green]",
                    "Canceled": "[dim]Canceled[/dim]",
                    "Open": "[yellow]Open[/yellow]"}.get(t["status"], t["status"])
            pnl = t["pnl"]
            pnl_c = "green" if pnl >= 0 else "red"
            fees = t["trading_fees"] + t["funding_cost"]
            table.add_row(
                t["id"], dir_m, st_m,
                f"[{pnl_c}]{pnl:+,}[/{pnl_c}]",
                f"{fees:,}",
                f"{t['margin']:,}",
                f"{t['leverage']:.1f}x",
                f"${t['price']:,.0f}",
                f"${t['liquidation']:,.0f}",
                t["creation_date"][:10],
                t.get("notes", ""),
                key=t["id"],
            )

    def _refresh_charts(self) -> None:
        timeline = tr.get_pnl_timeline(self._trades)
        if not timeline:
            return
        dates      = [p["date"] for p in timeline]
        cumulative = [p["cumulative"] for p in timeline]
        per_trade  = [p["pnl"] for p in timeline]
        self.query_one("#chart-cumulative", PlotWidget).update_line(dates, cumulative)
        self.query_one("#chart-bars",       PlotWidget).update_bars(dates, per_trade)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_goto_dashboard(self) -> None:
        self.query_one(TabbedContent).active = "tab-dashboard"

    def action_goto_trades(self) -> None:
        self.query_one(TabbedContent).active = "tab-trades"

    def action_add_trade(self) -> None:
        self.push_screen(AddTradeModal(), self._on_added)

    def _on_added(self, trade: dict | None) -> None:
        if trade:
            self.notify(f"Trade {trade['id']} guardado.", severity="information", timeout=3)
            self._update_ui(self._current_price)

    def action_delete_trade(self) -> None:
        table = self.query_one("#trades-table", DataTable)
        if table.row_count == 0:
            self.notify("No hay trades.", severity="warning")
            return
        try:
            trade_id = str(table.get_row_at(table.cursor_row)[0])
            tr.delete_trade(trade_id)
            self.notify(f"Trade {trade_id} eliminado.", severity="warning", timeout=3)
            self._update_ui(self._current_price)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())


if __name__ == "__main__":
    BtcTuiApp().run()
