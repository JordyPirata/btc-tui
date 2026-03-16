"""BTC Portfolio TUI — visualiza tus trades y rendimientos a largo plazo."""
from __future__ import annotations

from datetime import date, datetime

import plotext as plt
import requests
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
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


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------


class PlotWidget(Static):
    """Terminal chart powered by plotext."""

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

    def on_mount(self) -> None:
        self._redraw()

    def on_resize(self) -> None:
        self._redraw()

    def update_data(self, dates: list[str], values: list[float]) -> None:
        self._dates = dates
        self._values = values
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
            plt.plot(x, self._values, marker="braille")
            step = max(1, len(x) // 6)
            tick_x = x[::step]
            tick_labels = [self._dates[i][:7] for i in tick_x]
            plt.xticks(tick_x, tick_labels)
        else:
            plt.text("Sin datos — agrega trades con [A]", x=1, y=1)

        self.update(Text.from_ansi(plt.build()))


class StatCard(Static):
    """Tarjeta de métrica con label y valor."""

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
        self._value = "—"
        self._color = "white"

    def on_mount(self) -> None:
        self._refresh()

    def set_value(self, value: str, color: str = "white") -> None:
        self._value = value
        self._color = color
        self._refresh()

    def _refresh(self) -> None:
        self.update(
            f"[dim]{self._label}[/dim]\n[bold {self._color}]{self._value}[/bold {self._color}]"
        )


# ---------------------------------------------------------------------------
# Modal: Agregar Trade
# ---------------------------------------------------------------------------


class AddTradeModal(ModalScreen):
    DEFAULT_CSS = """
    AddTradeModal {
        align: center middle;
    }
    AddTradeModal > Vertical {
        width: 62;
        height: auto;
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
    AddTradeModal Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        today = date.today().isoformat()
        with Vertical():
            yield Label("[bold]➕ Agregar Trade[/bold]", id="modal-title")
            yield Label("Tipo")
            yield Select(
                [("🟢 Compra (BUY)", "buy"), ("🔴 Venta (SELL)", "sell")],
                id="trade-type",
                value="buy",
            )
            yield Label("Fecha (YYYY-MM-DD)")
            yield Input(value=today, id="trade-date", placeholder="2024-01-15")
            yield Label("Cantidad BTC")
            yield Input(id="trade-btc", placeholder="0.001")
            yield Label("Precio USD/BTC en esa fecha")
            yield Input(id="trade-price", placeholder="50000")
            yield Label("Notas (opcional)")
            yield Input(id="trade-notes", placeholder="Binance, DCA, etc.")
            with Horizontal():
                yield Button("Guardar", id="btn-save", variant="primary")
                yield Button("Cancelar", id="btn-cancel", variant="default")

    @on(Button.Pressed, "#btn-save")
    def save(self) -> None:
        trade_type = self.query_one("#trade-type", Select).value
        trade_date = self.query_one("#trade-date", Input).value.strip()
        btc_str = self.query_one("#trade-btc", Input).value.strip()
        price_str = self.query_one("#trade-price", Input).value.strip()
        notes = self.query_one("#trade-notes", Input).value.strip()

        try:
            datetime.strptime(trade_date, "%Y-%m-%d")
            btc_amount = float(btc_str)
            price_usd = float(price_str)
            if btc_amount <= 0 or price_usd <= 0:
                raise ValueError
        except (ValueError, TypeError):
            self.notify("⚠ Revisa los datos: fecha, BTC y precio deben ser válidos.", severity="error")
            return

        if trade_type is Select.BLANK:
            self.notify("⚠ Selecciona el tipo de operación.", severity="error")
            return

        trade = tr.add_trade(trade_type, trade_date, btc_amount, price_usd, notes)
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

    #stats-row {
        height: 5;
        margin: 0 0 1 0;
    }
    #charts-row {
        height: 1fr;
    }
    #trades-controls {
        height: 3;
        margin-bottom: 1;
    }
    #trades-controls Button {
        margin-right: 1;
    }
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
                    yield StatCard("BTC Balance", id="stat-btc")
                    yield StatCard("Total Invertido", id="stat-invested")
                    yield StatCard("Valor Actual", id="stat-value")
                    yield StatCard("P&L", id="stat-pnl")
                    yield StatCard("ROI", id="stat-roi")
                    yield StatCard("Precio BTC", id="stat-price")
                with Horizontal(id="charts-row"):
                    yield PlotWidget("₿ BTC Acumulado", id="chart-btc")
                    yield PlotWidget("💵 USD Neto Invertido", id="chart-invested")
            with TabPane("📋 Trades", id="tab-trades"):
                with Horizontal(id="trades-controls"):
                    yield Button("➕ Agregar [A]", id="btn-add", variant="primary")
                    yield Button("🗑 Eliminar [D]", id="btn-delete", variant="error")
                    yield Static("Cargando precio...", id="info-label")
                yield DataTable(id="trades-table", zebra_stripes=True, cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#trades-table", DataTable)
        table.add_columns("ID", "Tipo", "Fecha", "BTC", "Precio USD", "Total USD", "Notas")
        self.action_refresh_data()

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def action_refresh_data(self) -> None:
        self.notify("Actualizando precio BTC...", timeout=2)
        self._fetch_and_update()

    @work(thread=True)
    def _fetch_and_update(self) -> None:
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

        self.query_one("#stat-btc", StatCard).set_value(f"₿ {s['btc']:.6f}", "yellow")
        self.query_one("#stat-invested", StatCard).set_value(f"${s['invested']:,.2f}", "white")

        val_color = "green" if s["current_val"] >= s["net_cost"] else "red"
        self.query_one("#stat-value", StatCard).set_value(f"${s['current_val']:,.2f}", val_color)

        pnl_sign = "+" if s["pnl"] >= 0 else ""
        pnl_color = "green" if s["pnl"] >= 0 else "red"
        self.query_one("#stat-pnl", StatCard).set_value(f"{pnl_sign}${s['pnl']:,.2f}", pnl_color)

        roi_sign = "+" if s["roi"] >= 0 else ""
        roi_color = "green" if s["roi"] >= 0 else "red"
        self.query_one("#stat-roi", StatCard).set_value(f"{roi_sign}{s['roi']:.1f}%", roi_color)

        price_str = f"${self._current_price:,.2f}" if self._current_price else "N/A (offline)"
        self.query_one("#stat-price", StatCard).set_value(price_str, "cyan")

        avg = f"${s['avg_price']:,.2f}" if s["avg_price"] else "N/A"
        self.query_one("#info-label", Static).update(
            f"BTC: [cyan]{price_str}[/cyan]  Precio promedio compra: [yellow]{avg}[/yellow]"
        )

    def _refresh_table(self) -> None:
        table = self.query_one("#trades-table", DataTable)
        table.clear()
        for t in reversed(self._trades):
            tipo = "[green]BUY[/green]" if t["type"] == "buy" else "[red]SELL[/red]"
            table.add_row(
                t["id"],
                tipo,
                t["date"],
                f"₿ {t['btc_amount']:.6f}",
                f"${t['price_usd']:,.2f}",
                f"${t['total_usd']:,.2f}",
                t.get("notes", ""),
                key=t["id"],
            )

    def _refresh_charts(self) -> None:
        timeline = tr.get_timeline(self._trades)
        if not timeline:
            return
        dates = [p["date"] for p in timeline]
        self.query_one("#chart-btc", PlotWidget).update_data(dates, [p["btc"] for p in timeline])
        self.query_one("#chart-invested", PlotWidget).update_data(dates, [p["invested"] for p in timeline])

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_add_trade(self) -> None:
        self.push_screen(AddTradeModal(), self._on_trade_added)

    @on(Button.Pressed, "#btn-add")
    def on_btn_add(self) -> None:
        self.action_add_trade()

    def _on_trade_added(self, trade: dict | None) -> None:
        if trade:
            self.notify(f"✅ Trade {trade['id']} guardado.", severity="information")
            self._update_ui(self._current_price)

    def action_delete_trade(self) -> None:
        table = self.query_one("#trades-table", DataTable)
        if table.row_count == 0:
            self.notify("No hay trades para eliminar.", severity="warning")
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
