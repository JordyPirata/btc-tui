"""Reusable TUI widgets."""
from __future__ import annotations

import plotext as plt
from rich.text import Text
from textual.widgets import Static


def fmt_sats(n: int) -> str:
    sign = "+" if n > 0 else ""
    return f"{sign}{n:,}"


class PlotWidget(Static):
    """Terminal chart using plotext, updatable with line or bar mode."""

    DEFAULT_CSS = """
    PlotWidget {
        width: 1fr;
        height: 100%;
        border: solid $panel-darken-2 60%;
        background: transparent;
    }
    """

    def __init__(self, title: str = "", **kwargs) -> None:
        super().__init__("", markup=False, **kwargs)
        self._title    = title
        self._dates:  list[str]   = []
        self._values: list[float] = []
        self._bar_mode = False

    def on_mount(self)  -> None: self._redraw()
    def on_resize(self) -> None: self._redraw()

    def update_line(self, dates: list[str], values: list[float]) -> None:
        self._dates, self._values, self._bar_mode = dates, values, False
        self._redraw()

    def update_bars(self, dates: list[str], values: list[float]) -> None:
        self._dates, self._values, self._bar_mode = dates, values, True
        self._redraw()

    def _redraw(self) -> None:
        w = max(self.size.width - 2, 30)
        h = max(self.size.height - 2, 5)

        plt.clf()
        plt.plotsize(w, h)
        plt.title(self._title)
        plt.theme("dark")

        if self._dates and self._values:
            x = list(range(len(self._dates)))
            if self._bar_mode:
                plt.bar(x, [max(v, 0) for v in self._values], color="green")
                plt.bar(x, [min(v, 0) for v in self._values], color="red")
            else:
                plt.plot(x, self._values, marker="braille")
                plt.hline(0, "white")
            step = max(1, len(x) // 6)
            plt.xticks(x[::step], [self._dates[i] for i in x[::step]])
        else:
            plt.text("No data  —  press [A] to add your first trade", x=1, y=1)

        try:
            self.update(Text.from_ansi(plt.build()))
        except (ValueError, IndexError):
            self.update("")
