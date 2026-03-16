"""BTC Futures TUI — P&L en sats, spot acumulado en USD."""
from __future__ import annotations

from datetime import datetime

import plotext as plt
import requests
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
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


def fetch_btc_price() -> float:
    try:
        r = requests.get(BTC_PRICE_URL, timeout=6)
        return float(r.json()["bitcoin"]["usd"])
    except Exception:
        return 0.0


def fmt_sats(n: int) -> str:
    """Formatea sats con signo y separadores de miles."""
    sign = "+" if n > 0 else ""
    return f"{sign}{n:,} sats"


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------


class PlotWidget(Static):
    DEFAULT_CSS = """
    PlotWidget {
        width: 1fr;
        height: 100%;
        border: solid $accent;
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
        self._dates = dates
        self._values = values
        self._bar_mode = False
        self._redraw()

    def update_bars(self, dates: list[str], values: list[float]) -> None:
        self._dates = dates
        self._values = values
        self._bar_mode = True
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
                colors = ["green" if v >= 0 else "red" for v in self._values]
                plt.bar(x, self._values, color=colors)
            else:
                plt.plot(x, self._values, marker="braille")
                plt.hline(0, "white")

            step = max(1, len(x) // 6)
            plt.xticks(x[::step], [self._dates[i] for i in x[::step]])
        else:
            plt.text("Sin datos — agrega trades con [A]", x=1, y=1)

        self.update(Text.from_ansi(plt.build()))


class StatCard(Static):
    DEFAULT_CSS = """
    StatCard {
        width: 1fr;
        height: 5;
        border: solid $panel;
        padding: 0 1;
        content-align: center middle;
        text-align: center;
    }
    """

    def __init__(self, label: str, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._label = label

    def on_mount(self) -> None:
        self._draw("—", "white")

    def set_value(self, value: str, color: str = "white") -> None:
        self._draw(value, color)

    def _draw(self, value: str, color: str) -> None:
        self.update(f"[dim]{self._label}[/dim]\n[bold {color}]{value}[/bold {color}]")


# ---------------------------------------------------------------------------
# Modal: Agregar Trade
# ---------------------------------------------------------------------------


class AddTradeModal(ModalScreen):
    DEFAULT_CSS = """
    AddTradeModal { align: center middle; }
    AddTradeModal > ScrollableContainer {
        width: 66;
        height: 90%;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    AddTradeModal Label {
        margin-top: 1;
        color: $text-muted;
    }
    AddTradeModal #modal-title {
        text-align: center;
        margin-bottom: 1;
        color: $text;
    }
    AddTradeModal Horizontal {
        margin-top: 1;
        height: auto;
    }
    AddTradeModal Button { width: 1fr; margin: 0 1; }
    """

    def compose(self) -> ComposeResult:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with ScrollableContainer():
            yield Label("[bold]Agregar Trade[/bold]", id="modal-title")

            yield Label("Dirección")
            yield Select([("Long ↑", "Long"), ("Short ↓", "Short")], id="f-direction", value="Long")

            yield Label("Estado")
            yield Select(
                [("Filled ✅", "Filled"), ("Canceled ❌", "Canceled"), ("Open 🔄", "Open")],
                id="f-status", value="Filled",
            )

            yield Label("P&L (sats)")
            yield Input(id="f-pnl", placeholder="0  (negativo si fue pérdida)")

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
            yield Input(value=now, id="f-created", placeholder="2026-02-08 20:41")

            yield Label("Fecha filled (dejar vacío si no aplica)")
            yield Input(id="f-filled", placeholder="2026-02-08 22:10")

            yield Label("ID externo (opcional)")
            yield Input(id="f-id", placeholder="e0ad7f33-c690...")

            yield Label("Notas")
            yield Input(id="f-notes", placeholder="Estrategia, contexto...")

            with Horizontal():
                yield Button("Guardar", id="btn-save", variant="primary")
                yield Button("Cancelar", id="btn-cancel")

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

    @on(Button.Pressed, "#btn-save")
    def save(self) -> None:
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

        fields = {
            "id": self._get("#f-id"),
            "direction": direction,
            "status": status,
            "pnl": self._int("#f-pnl"),
            "quantity": self._int("#f-quantity"),
            "trade_margin": self._int("#f-trade-margin"),
            "margin": self._int("#f-margin"),
            "leverage": self._float("#f-leverage"),
            "price": self._float("#f-price"),
            "liquidation": self._float("#f-liquidation"),
            "stoploss": self._float("#f-sl"),
            "takeprofit": self._float("#f-tp"),
            "trading_fees": self._int("#f-fees"),
            "funding_cost": self._int("#f-funding"),
            "creation_date": created,
            "filled_date": self._get("#f-filled"),
            "notes": self._get("#f-notes"),
        }
        trade = tr.add_trade(fields)
        self.dismiss(trade)

    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# App principal
# ---------------------------------------------------------------------------


class BtcTuiApp(App):
    CSS = """
    Screen { background: $background; }
    #stats-row  { height: 5; margin: 0 0 1 0; }
    #charts-row { height: 1fr; }
    #trades-controls { height: 3; margin-bottom: 1; }
    #trades-controls Button { margin-right: 1; }
    #info-label {
        width: 1fr;
        content-align: right middle;
        color: $text-muted;
        padding-right: 1;
    }
    DataTable { height: 1fr; }
    """

    BINDINGS = [
        ("r", "refresh_data", "Actualizar precio"),
        ("a", "add_trade", "Agregar"),
        ("d", "delete_trade", "Eliminar"),
        ("q", "quit", "Salir"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._current_price = 0.0
        self._trades: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("📊 Dashboard", id="tab-dashboard"):
                with Horizontal(id="stats-row"):
                    yield StatCard("P&L Neto", id="stat-pnl")
                    yield StatCard("Fees Totales", id="stat-fees")
                    yield StatCard("Win Rate", id="stat-winrate")
                    yield StatCard("Mejor Trade", id="stat-best")
                    yield StatCard("Peor Trade", id="stat-worst")
                    yield StatCard("Spot Acumulado (USD)", id="stat-spot")
                with Horizontal(id="charts-row"):
                    yield PlotWidget("P&L Acumulado (sats)", id="chart-cumulative")
                    yield PlotWidget("P&L por Trade (sats)", id="chart-bars")
            with TabPane("📋 Trades", id="tab-trades"):
                with Horizontal(id="trades-controls"):
                    yield Button("➕ Agregar [A]", id="btn-add", variant="primary")
                    yield Button("🗑 Eliminar [D]", id="btn-delete", variant="error")
                    yield Static("", id="info-label")
                yield DataTable(id="trades-table", zebra_stripes=True, cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#trades-table", DataTable)
        table.add_columns(
            "ID", "Dir", "Estado", "P&L (sats)", "Fees (sats)",
            "Margin (sats)", "Lev", "Entrada", "Liq.", "Creación", "Notas",
        )
        self.action_refresh_data()

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def action_refresh_data(self) -> None:
        self.notify("Actualizando precio BTC...", timeout=2)
        self._fetch()

    @work(thread=True)
    def _fetch(self) -> None:
        price = fetch_btc_price()
        self.call_from_thread(self._update_ui, price)

    def _update_ui(self, price: float) -> None:
        self._current_price = price
        self._trades = tr.load_trades()
        self._refresh_stats()
        self._refresh_table()
        self._refresh_charts()

    def _refresh_stats(self) -> None:
        s = tr.compute_stats(self._trades, self._current_price)

        pnl_color = "green" if s["net_pnl"] >= 0 else "red"
        self.query_one("#stat-pnl", StatCard).set_value(fmt_sats(s["net_pnl"]), pnl_color)

        self.query_one("#stat-fees", StatCard).set_value(f"{s['total_fees']:,} sats", "yellow")

        wr_color = "green" if s["win_rate"] >= 50 else "red"
        self.query_one("#stat-winrate", StatCard).set_value(
            f"{s['win_rate']:.1f}%  ({s['winners']}W / {s['losers']}L)", wr_color
        )

        self.query_one("#stat-best", StatCard).set_value(fmt_sats(s["best"]), "green")
        self.query_one("#stat-worst", StatCard).set_value(fmt_sats(s["worst"]), "red")

        spot_color = "green" if s["spot_usd"] >= 0 else "red"
        price_str = f"${self._current_price:,.0f}" if self._current_price else "offline"
        self.query_one("#stat-spot", StatCard).set_value(f"${s['spot_usd']:,.2f}", spot_color)

        self.query_one("#info-label", Static).update(
            f"BTC: [cyan]{price_str}[/cyan]  "
            f"Trades: [white]{s['filled']} filled[/white] / {s['canceled']} canceled"
        )

    def _refresh_table(self) -> None:
        table = self.query_one("#trades-table", DataTable)
        table.clear()
        for t in reversed(self._trades):
            dir_markup = "[green]Long ↑[/green]" if t["direction"] == "Long" else "[red]Short ↓[/red]"
            status_markup = {
                "Filled":   "[green]Filled[/green]",
                "Canceled": "[dim]Canceled[/dim]",
                "Open":     "[yellow]Open[/yellow]",
            }.get(t["status"], t["status"])
            pnl = t["pnl"]
            pnl_markup = f"[{'green' if pnl >= 0 else 'red'}]{pnl:+,}[/{'green' if pnl >= 0 else 'red'}]"
            fees = t["trading_fees"] + t["funding_cost"]
            table.add_row(
                t["id"],
                dir_markup,
                status_markup,
                pnl_markup,
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
        dates = [p["date"] for p in timeline]
        cumulative = [p["cumulative"] for p in timeline]
        per_trade = [p["pnl"] for p in timeline]

        self.query_one("#chart-cumulative", PlotWidget).update_line(dates, cumulative)
        self.query_one("#chart-bars", PlotWidget).update_bars(dates, per_trade)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_add_trade(self) -> None:
        self.push_screen(AddTradeModal(), self._on_added)

    @on(Button.Pressed, "#btn-add")
    def on_btn_add(self) -> None:
        self.action_add_trade()

    def _on_added(self, trade: dict | None) -> None:
        if trade:
            self.notify(f"✅ Trade {trade['id']} guardado.", severity="information")
            self._update_ui(self._current_price)

    def action_delete_trade(self) -> None:
        table = self.query_one("#trades-table", DataTable)
        if table.row_count == 0:
            self.notify("No hay trades.", severity="warning")
            return
        try:
            row = table.get_row_at(table.cursor_row)
            trade_id = str(row[0])
            tr.delete_trade(trade_id)
            self.notify(f"🗑 Trade {trade_id} eliminado.", severity="warning")
            self._update_ui(self._current_price)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-delete")
    def on_btn_delete(self) -> None:
        self.action_delete_trade()


if __name__ == "__main__":
    BtcTuiApp().run()
