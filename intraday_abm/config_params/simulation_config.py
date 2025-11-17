from dataclasses import dataclass


@dataclass
class SimulationConfig:
    """
    Zentrale Konfiguration für die Intraday-Simulation.
    Alle Parameter sind hier gebündelt und wissenschaftlich sauber dokumentierbar.
    """
    # Simulationshorizont
    n_steps: int = 200

    # Referenzpreis (z.B. Day-Ahead-Preis)
    da_price: float = 50.0

    # Seed zur Reproduzierbarkeit
    seed: int = 42

    # Preisrange für RandomLiquidityAgent
    random_min_price: float = 30.0
    random_max_price: float = 70.0

    # Volumenrange
    min_volume: float = 1.0
    max_volume: float = 10.0

    # Anzahl Random-Liquidity-Agenten
    n_random_agents: int = 20

    # Trend-Agent verwenden?
    use_trend_agent: bool = True


# Standard-Config
DEFAULT_CONFIG = SimulationConfig()
