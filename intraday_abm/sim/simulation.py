from __future__ import annotations

import random

from intraday_abm.core.order_book import OrderBook
from intraday_abm.core.market_operator import MarketOperator
from intraday_abm.core.types import PublicInfo, TopOfBook
from intraday_abm.agents.random_liquidity import RandomLiquidityAgent
from intraday_abm.agents.simple_trend import SimpleTrendAgent
from intraday_abm.config_params import SimulationConfig, DEFAULT_CONFIG


def run_demo(config: SimulationConfig | None = None):
    """
    Führt eine Intraday-Simulation mit gegebener Konfiguration aus.

    Kernidee:
    - MarketOperator + OrderBook
    - mehrere Agenten, die in jedem Zeitschritt Orders platzieren
    - Shinde-nahes Verhalten: Cancel-First + PublicInfo (TOB + DA-Preis)
    """
    if config is None:
        config = DEFAULT_CONFIG

    rng = random.Random(config.seed)

    # Ein Orderbuch für ein Produkt (product_id = 0)
    order_book = OrderBook(product_id=0)
    mo = MarketOperator(order_book=order_book)

    agents: list = []

    # Random-Liquidity-Agents
    for i in range(config.n_random_agents):
        agent = RandomLiquidityAgent.create(
            id=i + 1,
            rng=rng,
            capacity=100.0,
            min_price=config.random_min_price,
            max_price=config.random_max_price,
            min_volume=config.min_volume,
            max_volume=config.max_volume,
        )
        agents.append(agent)

    # Optional: Trend-Agent
    if config.use_trend_agent:
        trend_agent = SimpleTrendAgent.create(
            id=100,
            rng=rng,
            capacity=100.0,
            base_volume=5.0,
        )
        agents.append(trend_agent)

    # Log-Struktur
    log = {
        "t": [],
        "best_bid": [],
        "best_ask": [],
        "midprice": [],
        "spread": [],
        "book_size": [],
        "trades": [],
    }

    # Hauptloop
    for t in range(config.n_steps):
        trades_this_step = 0

        # zufällige Auswahl aktiver Agenten (vereinfacht)
        n_active = rng.randint(1, len(agents))
        active_agents = rng.sample(agents, n_active)

        for agent in active_agents:

            # Shinde-nah: zuerst eigene Orders canceln
            mo.cancel_agent_orders(agent.id)

            # TOB holen
            tob_raw = mo.get_tob()
            tob = TopOfBook(
                best_bid_price=tob_raw["best_bid_price"],
                best_bid_volume=None,   # aktuell noch nicht im Modell enthalten
                best_ask_price=tob_raw["best_ask_price"],
                best_ask_volume=None,   # optional für spätere Erweiterung
            )

            # Public Info
            public_info = PublicInfo(
                tob=tob,
                da_price=config.da_price,
            )

            # Order-Entscheidung
            order = agent.decide_order(t, public_info)

            if order is not None:
                trades = mo.process_order(order, time=t)
                trades_this_step += len(trades)

        # --- Logging ---
        tob_end = mo.get_tob()
        bb = tob_end["best_bid_price"]
        ba = tob_end["best_ask_price"]

        if bb is not None and ba is not None:
            mid = 0.5 * (bb + ba)
            spread = ba - bb
        else:
            mid = None
            spread = None

        log["t"].append(t)
        log["best_bid"].append(bb)
        log["best_ask"].append(ba)
        log["midprice"].append(mid)
        log["spread"].append(spread)
        log["book_size"].append(len(mo.order_book))
        log["trades"].append(trades_this_step)

        print(
            f"[t={t}] TOB bid: {bb} ask: {ba} "
            f"mid: {mid} spread: {spread} "
            f"book_size: {len(mo.order_book)} trades: {trades_this_step}"
        )

    return log, mo


if __name__ == "__main__":
    run_demo()
