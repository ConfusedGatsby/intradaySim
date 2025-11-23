from __future__ import annotations

import random

from intraday_abm.core.order_book import OrderBook
from intraday_abm.core.market_operator import MarketOperator
from intraday_abm.core.types import PublicInfo, TopOfBook, Side
from intraday_abm.agents.random_liquidity import RandomLiquidityAgent
from intraday_abm.agents.simple_trend import SimpleTrendAgent
from intraday_abm.agents.dispatchable import DispatchableAgent
from intraday_abm.agents.variable import VariableAgent
from intraday_abm.config_params import SimulationConfig, DEFAULT_CONFIG


def run_demo(config: SimulationConfig | None = None):
    """
    Führt eine Intraday-Simulation mit gegebener Konfiguration aus.

    Kernidee:
    - MarketOperator + OrderBook
    - mehrere Agententypen:
      - RandomLiquidityAgent (synthetischer Orderflow)
      - DispatchableAgent (Thermal, Shinde-inspiriert)
      - VariableAgent (RES/variable Last, Shinde-inspiriert)
      - optional SimpleTrendAgent
    - Shinde-nah:
      - Cancel-First pro Agent
      - PublicInfo (TOB + DA-Preis)
      - AgentPrivateInfo mit Position/Revenue-Updates (A2)
    """
    if config is None:
        config = DEFAULT_CONFIG

    rng = random.Random(config.seed)

    # Ein Orderbuch für ein Produkt (product_id = 0)
    order_book = OrderBook(product_id=0)
    mo = MarketOperator(order_book=order_book)

    agents = []
    next_id = 1

    # Random-Liquidity-Agents
    for _ in range(config.n_random_agents):
        ag = RandomLiquidityAgent.create(
            id=next_id,
            rng=rng,
            capacity=100.0,
            min_price=config.random_min_price,
            max_price=config.random_max_price,
            min_volume=config.min_volume,
            max_volume=config.max_volume,
        )
        agents.append(ag)
        next_id += 1

    # Dispatchable Agents
    for _ in range(config.n_dispatchable_agents):
        d_ag = DispatchableAgent.create(
            id=next_id,
            rng=rng,
            capacity=config.dispatchable_capacity,
            da_position=config.dispatchable_da_position,
            marginal_cost=config.dispatchable_marginal_cost,
            base_volume=config.dispatchable_base_volume,
            epsilon_price=config.dispatchable_epsilon_price,
        )
        agents.append(d_ag)
        next_id += 1

    # Variable Agents
    for _ in range(config.n_variable_agents):
        v_ag = VariableAgent.create(
            id=next_id,
            rng=rng,
            capacity=config.variable_capacity,
            base_forecast=config.variable_base_forecast,
            base_volume=config.variable_base_volume,
            imbalance_tolerance=config.variable_imbalance_tolerance,
        )
        agents.append(v_ag)
        next_id += 1

    # Optional: Trend-Agent
    if config.use_trend_agent:
        t_ag = SimpleTrendAgent.create(
            id=next_id,
            rng=rng,
            capacity=100.0,
            base_volume=5.0,
        )
        agents.append(t_ag)
        next_id += 1

    # Map von Agent-ID auf Agent-Objekt (für A2 notwendig)
    agent_by_id = {ag.id: ag for ag in agents}

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

        # einfache Aktivierung: alle Agents versuchen zu handeln
        # (kann später probabilistisch gemacht werden)
        for agent in agents:

            # Shinde-nah: zuerst eigene Orders canceln
            mo.cancel_agent_orders(agent.id)

            # TOB holen
            tob_raw = mo.get_tob()
            tob = TopOfBook(
                best_bid_price=tob_raw["best_bid_price"],
                best_bid_volume=None,
                best_ask_price=tob_raw["best_ask_price"],
                best_ask_volume=None,
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

                # Trades an beteiligte Agenten zurückmelden (A2)
                for tr in trades:
                    buyer = agent_by_id.get(tr.buy_agent_id)
                    seller = agent_by_id.get(tr.sell_agent_id)
                    if buyer is not None:
                        buyer.on_trade(tr.volume, tr.price, side=Side.BUY)
                    if seller is not None:
                        seller.on_trade(tr.volume, tr.price, side=Side.SELL)

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

    # Optional: kleine Zusammenfassung der Agenten am Ende
    print("\n=== Agenten-Zusammenfassung ===")
    for ag in agents:
        pi = ag.private_info
        print(
            f"Agent {ag.id} ({ag.__class__.__name__}): "
            f"pos={pi.market_position:.2f}, rev={pi.revenue:.2f}, "
            f"imbalance={pi.imbalance:.2f}"
        )

    return log, mo


if __name__ == "__main__":
    run_demo()
