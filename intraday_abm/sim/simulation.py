from __future__ import annotations

import random
from typing import Union, List

from intraday_abm.core.order_book import OrderBook
from intraday_abm.core.market_operator import MarketOperator
from intraday_abm.core.types import PublicInfo, TopOfBook, Side
from intraday_abm.core.order import Order
from intraday_abm.agents.random_liquidity import RandomLiquidityAgent
from intraday_abm.agents.simple_trend import SimpleTrendAgent
from intraday_abm.agents.dispatchable import DispatchableAgent
from intraday_abm.agents.variable import VariableAgent
from intraday_abm.agents.pricing_strategies import NaivePricingStrategy
from intraday_abm.config_params import SimulationConfig, DEFAULT_CONFIG


def create_pricing_strategy(config: SimulationConfig, rng) -> NaivePricingStrategy:
    """
    Erzeugt die global konfigurierte Preisstrategie für die Simulation.

    Phase 2:
    - Aktuell wird nur die NaivePricingStrategy unterstützt.
    - Die Parameter stammen zentral aus der SimulationConfig.
    - Später kann hier leicht auf MTAA o.ä. erweitert werden.
    """
    strategy_name = getattr(config, "pricing_strategy", "naive").lower()

    if strategy_name == "naive":
        return NaivePricingStrategy(
            rng=rng,
            pi_range=config.naive_pi_range,
            n_segments=config.naive_n_segments,
            n_orders=config.naive_n_orders,
            min_price=config.random_min_price,
            max_price=config.random_max_price,
        )

    raise NotImplementedError(
        f"Pricing-Strategie '{config.pricing_strategy}' ist noch nicht implementiert."
    )


def run_demo(config: SimulationConfig | None = None):
    if config is None:
        config = DEFAULT_CONFIG

    rng = random.Random(config.seed)
    order_book = OrderBook(product_id=0)
    mo = MarketOperator(order_book=order_book)

    # Phase 2: zentrale Preisstrategie erzeugen (aktuell: naive)
    pricing_strategy = create_pricing_strategy(config, rng)

    agents = []
    next_id = 1

    # Random-Liquidity-Agents -----------------------------------------------
    for _ in range(config.n_random_agents):
        ag = RandomLiquidityAgent.create(
            id=next_id,
            rng=rng,
            capacity=100.0,
            min_price=config.random_min_price,
            max_price=config.random_max_price,
            min_volume=config.min_volume,
            max_volume=config.max_volume,
            price_band_pi=config.naive_pi_range,
            n_segments=config.naive_n_segments,
            n_orders=config.naive_n_orders,
        )
        # Zuweisung der zentral konfigurierten Preisstrategie
        ag.pricing_strategy = pricing_strategy

        agents.append(ag)
        next_id += 1

    # Dispatchable Agents ---------------------------------------------------
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
        # Phase 2: DispatchableAgent behält vorerst seine interne Heuristik.
        # In Phase 3 kann hier ebenfalls eine PricingStrategy zugewiesen werden.
        agents.append(d_ag)
        next_id += 1

    # Variable Agents -------------------------------------------------------
    for _ in range(config.n_variable_agents):
        v_ag = VariableAgent.create(
            id=next_id,
            rng=rng,
            capacity=config.variable_capacity,
            base_forecast=config.variable_base_forecast,
            base_volume=config.variable_base_volume,
            imbalance_tolerance=config.variable_imbalance_tolerance,
        )
        # Phase 2: VariableAgent behält vorerst seine interne Heuristik.
        # In Phase 3 kann hier ebenfalls eine PricingStrategy zugewiesen werden.
        agents.append(v_ag)
        next_id += 1

    # Optionaler Trend-Agent ------------------------------------------------
    if config.use_trend_agent:
        t_ag = SimpleTrendAgent.create(
            id=next_id,
            rng=rng,
            capacity=100.0,
            base_volume=5.0,
        )
        agents.append(t_ag)
        next_id += 1

    agent_by_id = {ag.id: ag for ag in agents}

    log = {
        "t": [],
        "best_bid": [],
        "best_ask": [],
        "midprice": [],
        "spread": [],
        "book_size": [],
        "trades": [],
    }

    agent_logs = {
        ag.id: {
            "t": [],
            "agent_id": ag.id,
            "agent_type": ag.__class__.__name__,
            "position": [],
            "revenue": [],
            "imbalance": [],
            "da_position": [],
            "capacity": [],
        }
        for ag in agents
    }

    for t in range(config.n_steps):
        trades_this_step = 0

        # Agenten-States loggen (vor dem Handel)
        for ag in agents:
            pi = ag.private_info
            agent_logs[ag.id]["t"].append(t)
            agent_logs[ag.id]["position"].append(pi.market_position)
            agent_logs[ag.id]["revenue"].append(pi.revenue)
            agent_logs[ag.id]["imbalance"].append(pi.imbalance)
            agent_logs[ag.id]["da_position"].append(pi.da_position)
            agent_logs[ag.id]["capacity"].append(pi.effective_capacity)

        # Handelsrunde ------------------------------------------------------
        for agent in agents:
            # Cancel-first: alle offenen Orders des Agenten löschen
            mo.cancel_agent_orders(agent.id)

            tob_raw = mo.get_tob()
            tob = TopOfBook(
                best_bid_price=tob_raw["best_bid_price"],
                best_bid_volume=None,
                best_ask_price=tob_raw["best_ask_price"],
                best_ask_volume=None,
            )

            public_info = PublicInfo(
                tob=tob,
                da_price=config.da_price,
            )

            decision: Union[None, Order, List[Order]] = agent.decide_order(t, public_info)
            if decision is None:
                continue
            elif isinstance(decision, Order):
                orders = [decision]
            elif isinstance(decision, list):
                orders = decision
            else:
                # Unerwarteter Rückgabetyp
                continue

            for order in orders:
                trades = mo.process_order(order, time=t)
                trades_this_step += len(trades)

                for tr in trades:
                    buyer = agent_by_id.get(tr.buy_agent_id)
                    seller = agent_by_id.get(tr.sell_agent_id)
                    if buyer:
                        buyer.on_trade(tr.volume, tr.price, side=Side.BUY)
                    if seller:
                        seller.on_trade(tr.volume, tr.price, side=Side.SELL)

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

    print("\n=== Agenten-Zusammenfassung ===")
    for ag in agents:
        pi = ag.private_info
        print(
            f"Agent {ag.id} ({ag.__class__.__name__}): "
            f"pos={pi.market_position:.2f}, rev={pi.revenue:.2f}, "
            f"imbalance={pi.imbalance:.2f}"
        )

    return log, agent_logs, mo


if __name__ == "__main__":
    run_demo()
