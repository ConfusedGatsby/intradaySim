"""
Wrapper, um die Simulation direkt per 'Run Python File' in VS Code zu starten.
"""

from collections import Counter

from intraday_abm.sim.simulation import run_demo
from intraday_abm.config_params import DEFAULT_CONFIG


if __name__ == "__main__":

    # ---- WICHTIG ----
    # Wir verwenden AB JETZT ausschließlich die Config aus config_params.
    config = DEFAULT_CONFIG

    # Simulation starten
    log, mo = run_demo(config)

    # Summary berechnen
    n_steps = len(log["t"])
    total_trades = sum(log["trades"])
    avg_book_size = sum(log["book_size"]) / n_steps

    non_null_spreads = [s for s in log["spread"] if s is not None]
    avg_spread = (
        sum(non_null_spreads) / len(non_null_spreads)
        if non_null_spreads else None
    )

    # Agenten-Zusammenstellung basierend auf Config
    agent_types = []

    if config.n_random_agents > 0:
        agent_types += ["RandomLiquidityAgent"] * config.n_random_agents

    if config.use_trend_agent:
        agent_types.append("SimpleTrendAgent")

    agent_count = len(agent_types)
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
    print(f"Gesamtzahl Agenten:          {agent_count}")
    for agent_type, count in type_counts.items():
        print(f"  {agent_type}: {count}")
