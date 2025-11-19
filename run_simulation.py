"""
Einstiegspunkt, um die Simulation direkt in VS Code auszuführen.
"""

from collections import Counter

from intraday_abm.sim.simulation import run_demo
from intraday_abm.config_params import DEFAULT_CONFIG


if __name__ == "__main__":
    # Konfiguration vollständig aus config_params übernehmen
    config = DEFAULT_CONFIG

    log, mo = run_demo(config)

    n_steps = len(log["t"])
    total_trades = sum(log["trades"])
    avg_book_size = sum(log["book_size"]) / n_steps

    non_null_spreads = [s for s in log["spread"] if s is not None]
    avg_spread = (
        sum(non_null_spreads) / len(non_null_spreads)
        if non_null_spreads else None
    )

    # Agentenzusammensetzung aus Config
    agent_types: list[str] = []
    if config.n_random_agents > 0:
        agent_types += ["RandomLiquidityAgent"] * config.n_random_agents
    if config.use_trend_agent:
        agent_types.append("SimpleTrendAgent")

    type_counts = Counter(agent_types)

    print("\n=== Simulation Summary ===")
    print(f"Zeitschritte:                {n_steps}")
    print(f"Gesamtanzahl Trades:         {total_trades}")
    print(f"Ø Orderbuchgröße:            {avg_book_size:.2f}")
    if avg_spread is not None:
        print(f"Ø Spread (Bid/Ask):          {avg_spread:.2f}")
    else:
        print("Ø Spread (Bid/Ask):          n/a (nie beidseitig)")

    print("\n--- Agenten im Modell ---")
    print(f"Gesamtzahl Agenten:          {len(agent_types)}")
    for agent_type, count in type_counts.items():
        print(f"  {agent_type}: {count}")
