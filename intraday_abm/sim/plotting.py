# intraday_abm/sim/plotting.py

from __future__ import annotations

import csv
from typing import Dict, List, Optional

import matplotlib.pyplot as plt


def _read_sim_log(path: str) -> Dict[str, List]:
    """
    Liest das Markt-Log (sim_log_*.csv) ein.
    Erwartete Spalten (mit ';' als Trennzeichen):
      t, best_bid, best_ask, midprice, spread, book_size, trades
    """
    data: Dict[str, List] = {
        "t": [],
        "best_bid": [],
        "best_ask": [],
        "midprice": [],
        "spread": [],
        "book_size": [],
        "trades": [],
    }

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            # Zeitindex
            data["t"].append(int(row["t"]))

            # Helper zum Parsen von Floats mit möglichen "None"/""-Einträgen
            def parse_float(val: str) -> Optional[float]:
                val = val.strip()
                if val == "" or val.lower() == "none":
                    return None
                return float(val)

            data["best_bid"].append(parse_float(row.get("best_bid", "")))
            data["best_ask"].append(parse_float(row.get("best_ask", "")))
            data["midprice"].append(parse_float(row.get("midprice", "")))
            data["spread"].append(parse_float(row.get("spread", "")))

            # Ganzzahlen
            data["book_size"].append(int(row.get("book_size", "0") or 0))
            data["trades"].append(int(row.get("trades", "0") or 0))

    return data


def plot_results(path: str) -> None:
    """
    Plottet einfache Marktmetriken über der Zeit:
      - Midprice
      - Spread
      - Trades pro Tick

    Wird am Ende der Simulation aus simulation.main() aufgerufen.
    """
    data = _read_sim_log(path)

    t = data["t"]
    mid = data["midprice"]
    spread = data["spread"]
    trades = data["trades"]

    # Für mid und spread ignorieren wir None-Werte
    t_mid = [ti for ti, mi in zip(t, mid) if mi is not None]
    y_mid = [mi for mi in mid if mi is not None]

    t_spread = [ti for ti, sp in zip(t, spread) if sp is not None]
    y_spread = [sp for sp in spread if sp is not None]

    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 8))

    # 1) Midprice
    ax = axes[0]
    if y_mid:
        ax.plot(t_mid, y_mid)
    ax.set_ylabel("Midprice [€/MWh]")
    ax.set_title("Midprice über der Zeit")
    ax.grid(True, linestyle="--", alpha=0.4)

    # 2) Spread
    ax = axes[1]
    if y_spread:
        ax.plot(t_spread, y_spread)
    ax.set_ylabel("Spread [€/MWh]")
    ax.set_title("Bid/Ask-Spread über der Zeit")
    ax.grid(True, linestyle="--", alpha=0.4)

    # 3) Trades pro Tick
    ax = axes[2]
    ax.plot(t, trades)
    ax.set_xlabel("Zeitschritt t")
    ax.set_ylabel("Trades")
    ax.set_title("Anzahl Trades pro Zeitschritt")
    ax.grid(True, linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.show()
