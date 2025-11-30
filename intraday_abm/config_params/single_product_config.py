from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SimulationConfig:
    # Allgemeines
    n_steps: int = 200
    seed: int = 42

    # Day-Ahead-Preis (als Referenz)
    da_price: float = 50.0

    # Random-Liquidity-Agents
    n_random_agents: int = 10
    random_min_price: float = da_price - 20.0
    random_max_price: float = da_price + 20.0
    min_volume: float = 0.3
    max_volume: float = 2.0

    # Zusatzparameter für naive Preisstrategie (Shinde-nahe)
    # Diese Parameter steuern zentral die NaivePricingStrategy für alle
    # RandomLiquidityAgents (und können später auch für andere Agententypen
    # wie Dispatchable/Variable genutzt werden).
    naive_pi_range: float = 10.0       # Breite des Preisbands (z.B. ±10 €)
    naive_n_segments: int = 20         # Diskretisierung des Preisbands
    naive_n_orders: int = 5            # Anzahl Orders pro Schritt

    # Trend-Agent
    use_trend_agent: bool = True
    

    # Dispatchable Agents (Thermal)
    n_dispatchable_agents: int = 3
    dispatchable_capacity: float = 100.0
    dispatchable_da_position: float = 50.0
    dispatchable_marginal_cost: float = 10.0
    dispatchable_base_volume: float = 5.0
    dispatchable_epsilon_price: float = 1.0
    dispatchable_imbalance_penalty: float = 0.0  # €/MWh Abweichung

    # Variable Agents (z.B. Wind/PV)
    n_variable_agents: int = 5
    variable_capacity: float = 60.0
    variable_base_forecast: float = 20.0
    variable_base_volume: float = 5.0
    variable_imbalance_tolerance: float = 1.0
    variable_imbalance_penalty: float = 0.0      # €/MWh Abweichung

    # Logging / Export
    results_dir: str = "results"
    csv_filename: str = "sim_log_seed_42.csv"

    # Globale Auswahl der Preisstrategie (Vorbereitung für MTAA etc.).
    # Aktuell wird nur "naive" unterstützt und in der Simulation genutzt.
    pricing_strategy: str = "naive"


DEFAULT_CONFIG = SimulationConfig()
