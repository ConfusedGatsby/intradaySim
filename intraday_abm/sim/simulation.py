from __future__ import annotations

import random

from ..core.order_book import OrderBook
from ..core.market_operator import MarketOperator
from ..core.types import PublicInfo
from ..agents.random_liquidity import RandomLiquidityAgent
from ..agents.simple_trend import SimpleTrendAgent
from ..config_params import SimulationConfig, DEFAULT_CONFIG


def run_demo(config: SimulationConfig | None = None):
    """
    Führt eine Simulation mit der gegebenen Konfiguration aus.
    Wenn keine Konfiguration übergeben wird -> DEFAULT_CONFIG.
    """

    # 1) Konfiguration laden
    if config is None:
        config = DEFAULT_CONFIG

    # 2) RNG (reproduzierbar)
    rng = random.Random(config.seed)

    # 3) Marktkomponenten
    ob = OrderBook(product_id=0)
    mo = MarketOperator(order_book=ob)

    # 4) Agenten erstellen
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

    # 5) Logging vorbereiten
    log = {
        "t": [],
        "best_bid": [],
        "best_ask": [],
        "midprice": [],
        "spread": [],
        "book_size": [],
        "trades": [],
    }

    # 6) Haupt-Simulationsloop
    for t in range(config.n_steps):

        trades_this_step = 0

        # Zufällige Auswahl aktiver Agents
        n_active = rng.randint(1, len(agents))
        active_agents = rng.sample(agents, n_active)

        # --- Agentenaktionen ---
        for agent in active_agents:

            # Shinde-nah: vorher alle eigenen Orders löschen
            mo.cancel_agent_orders(agent.id)

            # TOB auslesen
            tob = mo.get_tob()

            # PublicInfo erzeugen (Shinde: public info = TOB + DA-Preis)
            public_info = PublicInfo(
                best_bid=tob["best_bid_price"],
                best_ask=tob["best_ask_price"],
                da_price=config.da_price,
            )

            # Agent entscheidet
            order = agent.decide_order(t, public_info)

            if order is not None:
                trades = mo.process_order(order, time=t)
                trades_this_step += len(trades)

        # --- Nach allen Orders: aktueller Marktstatus ---
        tob_end = mo.get_tob()
        bb = tob_end["best_bid_price"]
        ba = tob_end["best_ask_price"]

        # Midprice & Spread
        if bb is not None and ba is not None:
            mid = 0.5 * (bb + ba)
            spread = ba - bb
        else:
            mid = None
            spread = None

        # Logging
        log["t"].append(t)
        log["best_bid"].append(bb)
        log["best_ask"].append(ba)
        log["midprice"].append(mid)
        log["spread"].append(spread)
        log["book_size"].append(len(mo.order_book))
        log["trades"].append(trades_this_step)

        # Debug-Ausgabe
        print(
            f"[t={t}] TOB bid: {bb} ask: {ba} "
            f"mid: {mid} spread: {spread} "
            f"book_size: {len(mo.order_book)} trades: {trades_this_step}"
        )

    # 7) Rückgabe: Log + MarketOperator (Orderbuch etc.)
    return log, mo


# Ermöglicht "python -m intraday_abm.sim.simulation"
if __name__ == "__main__":
    run_demo()
