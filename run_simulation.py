"""
run_simulation.py

Einstiegspunkt für die Intraday-ABM-Simulation.

- Lädt eine SimulationConfig
- Führt run_demo() aus
- Speichert das Marktlog als CSV
- Speichert pro Agent ein eigenes CSV
- Gibt eine kleine Zusammenfassung über Markt- und Agentenstatistiken aus
"""

from __future__ import annotations

import os
from typing import Dict, Any, List

from intraday_abm.config_params import DEFAULT_CONFIG, SimulationConfig
from intraday_abm.sim.simulation import run_demo
from intraday_abm.sim.export_utils import save_log_to_csv
from intraday_abm.sim.export_agent_logs import save_agent_logs
from intraday_abm.sim.plot_results import plot_results


def _compute_summary_stats(log: Dict[str, List[Any]]) -> Dict[str, float]:
    """
    Berechnet einfache Kennzahlen aus dem Simulationslog.
    Erwartet ein Dictionary mit Schlüsseln:
      - "t"
      - "book_size"
      - "spread"
      - "trades"
    """
    n_steps = len(log["t"]) if log.get("t") else 0

    total_trades = sum(log.get("trades", [])) if n_steps > 0 else 0

    avg_book_size = (
        sum(log.get("book_size", [])) / n_steps
        if n_steps > 0 and log.get("book_size")
        else 0.0
    )

    # Spread nur über gültige (nicht-None) Werte mitteln
    spreads = [s for s in log.get("spread", []) if s is not None]
    avg_spread = sum(spreads) / len(spreads) if spreads else 0.0

    return {
        "n_steps": n_steps,
        "total_trades": total_trades,
        "avg_book_size": avg_book_size,
        "avg_spread": avg_spread,
    }


def main(config: SimulationConfig | None = None) -> None:
    """
    Führt die Simulation mit der gegebenen Konfiguration aus
    und schreibt Log/Statistiken nach stdout und CSV.
    """
    if config is None:
        config = DEFAULT_CONFIG

    # --- Simulation ausführen ---
    log, agent_logs, mo = run_demo(config)

    # --- Verzeichnis anlegen ---
    os.makedirs(config.results_dir, exist_ok=True)

    # --- Markt-CSV speichern ---
    csv_path = os.path.join(config.results_dir, config.csv_filename)
    save_log_to_csv(log, csv_path)

    # --- Agenten-CSV speichern ---
    save_agent_logs(agent_logs, config.results_dir)

    # --- Kennzahlen berechnen ---
    stats = _compute_summary_stats(log)

    print("\n=== Simulation Summary ===")
    print(f"Zeitschritte:                {stats['n_steps']}")
    print(f"Gesamtanzahl Trades:         {stats['total_trades']}")
    print(f"Ø Orderbuchgröße:            {stats['avg_book_size']:.2f}")
    print(f"Ø Spread (Bid/Ask):          {stats['avg_spread']:.2f}")

    # --- Agenten-Zusammenfassung (korrekt aus Config) ---
    n_random = config.n_random_agents
    n_dispatchable = getattr(config, "n_dispatchable_agents", 0)
    n_variable = getattr(config, "n_variable_agents", 0)
    n_trend = 1 if config.use_trend_agent else 0

    total_agents = n_random + n_dispatchable + n_variable + n_trend

    print("\n--- Agenten im Modell ---")
    print(f"Gesamtzahl Agenten:          {total_agents}")
    print(f"  RandomLiquidityAgent: {n_random}")
    print(f"  DispatchableAgent:    {n_dispatchable}")
    print(f"  VariableAgent:        {n_variable}")
    print(f"  SimpleTrendAgent:     {n_trend}")

    print(f"\nLog als CSV gespeichert unter: {csv_path}")
    print(f"Agenten-Logs im Ordner:        {os.path.join(config.results_dir, 'agent_logs')}")

    # Optional: Plot aufrufen (kannst du auskommentieren, wenn du keinen Plot willst)
    try:
        plot_results(csv_path)
    except Exception as e:
        print(f"Plot konnte nicht erzeugt werden (optional): {e}")


if __name__ == "__main__":
    main()
