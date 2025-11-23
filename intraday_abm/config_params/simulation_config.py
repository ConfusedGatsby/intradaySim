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
    n_random_agents: int = 3
    random_min_price: float = 10.0
    random_max_price: float = 90.0
    min_volume: float = 1.0
    max_volume: float = 10.0

    # Trend-Agent
    use_trend_agent: bool = True

    # Dispatchable Agents (Thermal)
    n_dispatchable_agents: int = 2
    dispatchable_capacity: float = 100.0
    dispatchable_da_position: float = 50.0
    dispatchable_marginal_cost: float = 45.0
    dispatchable_base_volume: float = 5.0
    dispatchable_epsilon_price: float = 1.0

    # Variable Agents (z.B. Wind/PV)
    n_variable_agents: int = 1
    variable_capacity: float = 80.0
    variable_base_forecast: float = 20.0
    variable_base_volume: float = 5.0
    variable_imbalance_tolerance: float = 1.0

    # Logging / Export
    results_dir: str = "results"
    csv_filename: str = "sim_log_seed_42.csv"


DEFAULT_CONFIG = SimulationConfig()
