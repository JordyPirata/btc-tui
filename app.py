"""Main application — orchestrates tabs, data, and actions."""
from __future__ import annotations

import requests
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Footer, Header, Static, TabbedContent, TabPane

import trades
import stats as st
import config as cfg
from widgets import PlotWidget, fmt_sats
from screens import AddSpotModal, AddTradeModal, HelpModal

BTC_PRICE_URL = (
    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
)


def fetch_btc_price() -> float:
    try:
        r = requests.get(BTC_PRICE_URL, timeout=6)
        return float(r.json()["bitcoin"]["usd"])
    except Exception:
        return 0.0


class BtcTuiApp(App):
    CSS = """
    Screen { background: transparent; }
    TabbedContent, ContentSwitcher, TabPane,
    Tabs, Tab, Horizontal, Vertical { background: transparent; }
    TabbedContent > TabPane { padding: 0; }

    #stats-bar, #trade-status, #spot-status {
        height: 1;
        background: $panel 60%;
        padding: 0 1;
    }
    #charts-row { height: 1fr; }
    DataTable   { height: 1fr; background: transparent; }
    """

    BINDINGS = [
        ("1",             "goto_dashboard", "Dashboard"),
        ("2",             "goto_trades",    "Trades"),
        ("3",             "goto_spot",      "Spot"),
        ("a",             "add_trade",      "Add trade"),
        ("s",             "add_spot",       "Add spot"),
        ("d",             "delete_row",     "Delete"),
        ("r",             "refresh_data",   "Refresh"),
        ("t",             "cycle_theme",    "Theme"),
        ("question_mark", "show_help",      "Help"),
        ("q",             "quit",           "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._price:  float      = 0.0
        self._trades: list[dict] = []
        self._spot:   list[dict] = []

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("Dashboard", id="tab-dashboard"):
                yield Static("", id="stats-bar")
                with Horizontal(id="charts-row"):
                    yield PlotWidget("Cumulative P&L (sats)", id="chart-cumulative")
                    yield PlotWidget("P&L per Trade (sats)",  id="chart-bars")
            with TabPane("Trades", id="tab-trades"):
                yield Static("", id="trade-status")
                yield DataTable(id="trades-table", zebra_stripes=True, cursor_type="row")
            with TabPane("Spot", id="tab-spot"):
                yield Static("", id="spot-status")
                yield DataTable(id="spot-table", zebra_stripes=True, cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self._config = cfg.load_config()
        self.theme   = self._config.get("theme", "textual-dark")
        self.title   = "BTC Futures"
        self.query_one("#trades-table", DataTable).add_columns(
            "ID", "Dir", "Status", "Gross P&L", "Fees",
            "Margin", "Lev", "Entry", "Close", "Date", "Net P&L", "Notes",
        )
        self.query_one("#spot-table", DataTable).add_columns(
            "ID", "Date", "Sats", "Notes",
        )
        self.action_refresh_data()

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def action_refresh_data(self) -> None:
        self._fetch()

    @work(thread=True)
    def _fetch(self) -> None:
        self.call_from_thread(self._update_ui, fetch_btc_price())

    def _update_ui(self, price: float) -> None:
        self._price  = price
        self._trades = trades.load_trades()
        self._spot   = trades.load_spot()
        s = st.compute_stats(self._trades, self._spot, price)

        sign = "+" if s["spot_usd"] >= 0 else ""
        self.sub_title = f"BTC ${price:,.0f}  │  Spot {sign}${s['spot_usd']:,.2f} USD"

        self._draw_stats_bar(s)
        self._draw_trade_status(s, price)
        self._draw_spot_status(s)
        self._draw_trades_table()
        self._draw_spot_table()
        self._draw_charts()

    # ------------------------------------------------------------------
    # Status bars
    # ------------------------------------------------------------------

    def _draw_stats_bar(self, s: dict) -> None:
        pnl_c  = "green" if s["net_pnl"]  >= 0 else "red"
        spot_c = "green" if s["spot_usd"] >= 0 else "red"
        wr_c   = "green" if s["win_rate"] >= 50 else "red"
        self.query_one("#stats-bar", Static).update(
            f"P&L [{pnl_c}]{fmt_sats(s['net_pnl'])} sats[/{pnl_c}]"
            f"   Fees [yellow]{s['total_fees']:,}[/yellow]"
            f"   Win [{wr_c}]{s['win_rate']:.0f}%[/{wr_c}]"
            f" [dim]({s['winners']}W·{s['losers']}L)[/dim]"
            f"   Best [green]{fmt_sats(s['best'])}[/green]"
            f"   Worst [red]{fmt_sats(s['worst'])}[/red]"
            f"   Spot [{spot_c}]{s['total_spot_sats']:+,} sats  ${s['spot_usd']:,.2f} USD[/{spot_c}]"
        )

    def _draw_trade_status(self, s: dict, price: float) -> None:
        price_str = f"${price:,.0f}" if price else "offline"
        self.query_one("#trade-status", Static).update(
            f"BTC [cyan]{price_str}[/cyan]"
            f"   [white]{s['filled']}[/white] filled · [dim]{s['canceled']} canceled[/dim]"
            f"   [dim]↑↓ navigate  ·  A add  ·  D delete[/dim]"
        )

    def _draw_spot_status(self, s: dict) -> None:
        c = "green" if s["total_spot_sats"] >= 0 else "red"
        self.query_one("#spot-status", Static).update(
            f"Total [{c}]{s['total_spot_sats']:+,} sats[/{c}]"
            f"   [dim]{len(self._spot)} entries  ·  S add  ·  D delete[/dim]"
        )

    # ------------------------------------------------------------------
    # Tables
    # ------------------------------------------------------------------

    def _draw_trades_table(self) -> None:
        table = self.query_one("#trades-table", DataTable)
        table.clear()
        for t in reversed(self._trades):
            pnl     = t["pnl"]
            fees    = t["trading_fees"] + t["funding_cost"]
            net_pnl = pnl - fees
            pnl_c   = "green" if pnl     >= 0 else "red"
            net_c   = "green" if net_pnl >= 0 else "red"
            table.add_row(
                t["id"],
                "[green]Long ↑[/green]" if t["direction"] == "Long" else "[red]Short ↓[/red]",
                {"Filled": "[green]Filled[/green]",
                 "Canceled": "[dim]Canceled[/dim]",
                 "Open": "[yellow]Open[/yellow]"}.get(t["status"], t["status"]),
                f"[{pnl_c}]{pnl:+,}[/{pnl_c}]",
                f"{fees:,}",
                f"{t['margin']:,}",
                f"{t['leverage']:.1f}x",
                f"${t['price']:,.0f}",
                {"none": "—", "liquidation": "[red]Liq 💀[/red]",
                 "stoploss": "[yellow]SL 🛑[/yellow]",
                 "takeprofit": "[green]TP ✅[/green]"}.get(t.get("close_event", "none"), "—"),
                t["creation_date"][:10],
                f"[{net_c}]{net_pnl:+,}[/{net_c}]",
                t.get("notes", ""),
                key=t["id"],
            )

    def _draw_spot_table(self) -> None:
        table = self.query_one("#spot-table", DataTable)
        table.clear()
        for e in reversed(self._spot):
            c = "green" if e["sats"] >= 0 else "red"
            table.add_row(
                e["id"], e["date"],
                f"[{c}]{e['sats']:+,}[/{c}]",
                e.get("notes", ""),
                key=e["id"],
            )

    # ------------------------------------------------------------------
    # Charts
    # ------------------------------------------------------------------

    def _draw_charts(self) -> None:
        timeline = st.pnl_timeline(self._trades)
        if not timeline:
            return
        dates = [p["date"] for p in timeline]
        self.query_one("#chart-cumulative", PlotWidget).update_line(
            dates, [p["cumulative"] for p in timeline])
        self.query_one("#chart-bars", PlotWidget).update_bars(
            dates, [p["pnl"] for p in timeline])

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        if len(self.screen_stack) > 1:  # modal active
            return False
        return True

    def action_goto_dashboard(self) -> None:
        self.query_one(TabbedContent).active = "tab-dashboard"

    def action_goto_trades(self) -> None:
        self.query_one(TabbedContent).active = "tab-trades"

    def action_goto_spot(self) -> None:
        self.query_one(TabbedContent).active = "tab-spot"

    # ------------------------------------------------------------------
    # Add
    # ------------------------------------------------------------------

    def action_add_trade(self) -> None:
        self.push_screen(AddTradeModal(), self._on_trade_added)

    def _on_trade_added(self, trade: dict | None) -> None:
        if trade:
            self.notify(f"Trade {trade['id']} saved.", timeout=3)
            self._update_ui(self._price)

    def action_add_spot(self) -> None:
        self.push_screen(AddSpotModal(), self._on_spot_added)

    def _on_spot_added(self, entry: dict | None) -> None:
        if entry:
            self.notify(f"Spot {entry['id']}: {entry['sats']:+,} sats saved.", timeout=3)
            self._update_ui(self._price)

    # ------------------------------------------------------------------
    # Delete (context-aware based on active tab)
    # ------------------------------------------------------------------

    def action_delete_row(self) -> None:
        active = self.query_one(TabbedContent).active
        if active == "tab-trades":
            self._delete_from("#trades-table", trades.delete_trade,    "Trade")
        elif active == "tab-spot":
            self._delete_from("#spot-table",   trades.delete_spot_entry, "Spot")

    def _delete_from(self, table_id: str, delete_fn, label: str) -> None:
        table = self.query_one(table_id, DataTable)
        if table.row_count == 0:
            self.notify("No entries found.", severity="warning")
            return
        try:
            row_id = str(table.get_row_at(table.cursor_row)[0])
            delete_fn(row_id)
            self.notify(f"{label} {row_id} deleted.", severity="warning", timeout=3)
            self._update_ui(self._price)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def action_cycle_theme(self) -> None:
        themes = cfg.THEMES
        current = self.theme
        next_theme = themes[(themes.index(current) + 1) % len(themes)] if current in themes else themes[0]
        self.theme = next_theme
        self._config["theme"] = next_theme
        cfg.save_config(self._config)
        self.notify(f"Theme: {next_theme}", timeout=2)

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())
