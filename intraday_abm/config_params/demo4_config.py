"""
Centralized Simulation Configuration

This module provides a comprehensive configuration system for the intraday market simulation.
All simulation parameters are centralized here for easy tuning and experimentation.

Usage:
    from intraday_abm.config_params.demo4_config import Demo4Config
    
    # Use default config
    config = Demo4Config()
    
    # Or customize
    config = Demo4Config(
        n_variable_agents=20,
        n_thermal_agents=10,
        base_da_price=55.0
    )
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Demo4Config:
    """
    Configuration for Demo 4: 96-Product Quarterly Simulation
    
    This configuration covers:
    - Market setup (products, timing)
    - Agent populations and parameters
    - Pricing strategies
    - Simulation runtime
    - Output settings
    """
    
    # ========== SIMULATION RUNTIME ==========
    n_steps: int = 1500
    """Total simulation steps (should be >= 96*4 for full product lifecycle)"""
    
    seed: int = 42
    """Random seed for reproducibility"""
    
    verbose: bool = True
    """Print progress during simulation"""
    
    # ========== MARKET SETUP ==========
    n_products: int = 96
    """Number of products (96 = 24 hours × 4 quarters)"""
    
    product_duration_minutes: int = 15
    """Duration of each product in minutes (15-min granularity)"""
    
    start_time_minutes: int = 1440
    """Start time for delivery (1440 = Day 2, 00:00)"""
    
    gate_open_offset_hours: int = 24
    """Hours before delivery when trading opens (24 = D-1)"""
    
    gate_close_offset_minutes: int = 5
    """Minutes before delivery when trading closes"""
    
    # ========== DAY-AHEAD PRICE MODELING ==========
    season: Literal['winter', 'summer', 'spring', 'fall'] = 'winter'
    """Season for DA price pattern (affects peak/off-peak ratio)"""
    
    base_da_price: float = 45.0
    """Base day-ahead price in €/MWh"""
    
    price_volatility: float = 5.0
    """Standard deviation for DA price volatility"""
    
    add_stochastic_volatility: bool = True
    """Add additional stochastic component to prices"""
    
    # ========== VARIABLE AGENTS (Wind/Solar) ==========
    n_variable_agents: int = 10
    """Number of Variable/Renewable agents"""
    
    variable_capacity: float = 150.0
    """Capacity per Variable agent in MW"""
    
    variable_base_volume: float = 15.0
    """Base order volume for Variable agents in MW"""
    
    variable_imbalance_tolerance: float = 5.0
    """Imbalance tolerance in MW"""
    
    # Variable Agent Limit Prices (linear progression)
    variable_limit_buy_start: float = 55.0
    """Starting limit buy price for first Variable agent"""
    
    variable_limit_buy_step: float = 3.0
    """Increment in limit buy per agent"""
    
    variable_limit_sell_start: float = 45.0
    """Starting limit sell price for first Variable agent"""
    
    variable_limit_sell_step: float = -1.5
    """Decrement in limit sell per agent (negative = decreasing)"""
    
    # Variable Agent Forecast Parameters
    variable_forecast_base_start: float = 40.0
    """Base forecast for first Variable agent in MW"""
    
    variable_forecast_base_step: float = 10.0
    """Increment in base forecast per agent"""
    
    variable_solar_share: float = 0.3
    """Share of solar in generation (0-1, rest is wind)"""
    
    variable_wind_share: float = 0.7
    """Share of wind in generation (0-1)"""
    
    variable_quarterly_variation: float = 5.0
    """Small variation between quarters in MW"""
    
    # ========== RANDOM LIQUIDITY AGENTS ==========
    n_random_liquidity_agents: int = 10
    """Number of RandomLiquidity agents (market makers)"""
    
    random_capacity: float = 400.0
    """Large capacity for liquidity provision in MW"""
    
    random_min_price: float = 15.0
    """Minimum price for random agent orders"""
    
    random_max_price: float = 120.0
    """Maximum price for random agent orders"""
    
    random_min_volume: float = 3.0
    """Minimum order volume in MW"""
    
    random_max_volume: float = 12.0
    """Maximum order volume in MW"""
    
    random_n_orders: int = 7
    """Number of orders per random agent per step"""
    
    # Random Agent Limit Prices (linear progression)
    random_limit_buy_start: float = 75.0
    """Starting limit buy for first Random agent"""
    
    random_limit_buy_step: float = 3.0
    """Increment per agent"""
    
    random_limit_sell_start: float = 25.0
    """Starting limit sell for first Random agent"""
    
    random_limit_sell_step: float = -1.0
    """Decrement per agent"""
    
    # Random Agent Pricing Strategy
    random_pi_range: float = 8.0
    """Price range for naive pricing strategy"""
    
    random_n_segments: int = 15
    """Number of price segments"""
    
    random_strategy_n_orders: int = 7
    """Orders per pricing strategy call"""
    
    random_seed_offset: int = 200
    """Seed offset for Random agent RNGs"""
    
    # ========== THERMAL AGENTS (Dispatchable with Ramping) ==========
    n_thermal_agents: int = 5
    """Number of Thermal/Dispatchable agents"""
    
    # Thermal Agent Parameters (linear progression)
    thermal_marginal_cost_start: float = 40.0
    """Marginal cost for first Thermal agent in €/MWh"""
    
    thermal_marginal_cost_step: float = 5.0
    """Increment in marginal cost per agent"""
    
    thermal_capacity_start: float = 200.0
    """Capacity for first Thermal agent in MW"""
    
    thermal_capacity_step: float = 50.0
    """Increment in capacity per agent"""
    
    thermal_ramping_rate_start: float = 30.0
    """Ramping rate for first agent in MW/hour"""
    
    thermal_ramping_rate_step: float = 10.0
    """Increment in ramping rate per agent"""
    
    thermal_switch_param_start: float = 0.4
    """Switch parameter for first agent (0-1)"""
    
    thermal_switch_param_step: float = 0.1
    """Increment in switch parameter per agent"""
    
    # Thermal Agent Fixed Parameters
    thermal_da_position_ratio: float = 0.6
    """Initial DA position as ratio of capacity"""
    
    thermal_base_volume: float = 15.0
    """Base order volume in MW"""
    
    thermal_epsilon_price: float = 2.0
    """Minimum profit margin in €/MWh"""
    
    thermal_min_stable_load_ratio: float = 0.25
    """Minimum stable load as ratio of capacity"""
    
    thermal_alpha: float = 0.3
    """Limit price update factor (Shinde 2021 Eq. 11)"""
    
    thermal_imbalance_price_plus_offset: float = 15.0
    """Positive imbalance price = MC + offset"""
    
    thermal_imbalance_price_minus_offset: float = 10.0
    """Negative imbalance price = MC - offset"""
    
    thermal_e_imb: float = 5.0
    """Imbalance price error variance"""
    
    thermal_nu_r: float = 1.0
    """Ramping scaling factor (Shinde 2023)"""
    
    thermal_limit_buy_offset: float = 20.0
    """Limit buy = MC + offset"""
    
    thermal_limit_sell_offset: float = 15.0
    """Limit sell = MC - offset"""
    
    # Thermal Pricing Strategy
    thermal_pi_range: float = 10.0
    """Price range for naive pricing"""
    
    thermal_n_segments: int = 20
    """Number of price segments"""
    
    thermal_strategy_n_orders: int = 7
    """Orders per pricing strategy call"""
    
    thermal_strategy_min_price: float = 15.0
    """Minimum price bound"""
    
    thermal_strategy_max_price: float = 120.0
    """Maximum price bound"""
    
    thermal_seed_offset: int = 500
    """Seed offset for Thermal agent RNGs"""
    
    # ========== OUTPUT SETTINGS ==========
    results_dir: str = "results"
    """Directory for output files"""
    
    export_csv: bool = True
    """Export results to CSV"""
    
    csv_filename: str = "demo4_simulation.csv"
    """CSV filename for export"""
    
    # ========== LOGGING SETTINGS ==========
    enable_logging: bool = True
    """Enable structured logging"""
    
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = 'INFO'
    """Logging level (DEBUG for detailed output)"""
    
    log_to_file: bool = True
    """Write logs to file"""
    
    log_filename: str = "simulation.log"
    """Log filename"""
    
    log_to_console: bool = True
    """Print logs to console"""
    
    # ========== ADVANCED SETTINGS ==========
    enable_debug_logging: bool = False
    """Enable detailed debug logging (slow for 96 products!)"""
    
    # Pricing strategy selection (for future extensions)
    pricing_strategy: Literal['naive', 'mtaa'] = 'naive'
    """Global pricing strategy type"""
    
    # ========== COMPUTED PROPERTIES ==========
    
    @property
    def total_agents(self) -> int:
        """Total number of agents in simulation"""
        return (
            self.n_variable_agents + 
            self.n_random_liquidity_agents + 
            self.n_thermal_agents
        )
    
    @property
    def total_simulation_time_minutes(self) -> int:
        """Total real-world time covered by simulation"""
        return self.n_products * self.product_duration_minutes
    
    @property
    def total_simulation_time_hours(self) -> float:
        """Total simulation time in hours"""
        return self.total_simulation_time_minutes / 60.0
    
    def get_variable_agent_params(self, agent_index: int) -> dict:
        """
        Get parameters for a specific Variable agent
        
        Args:
            agent_index: Index of agent (0 to n_variable_agents-1)
            
        Returns:
            Dictionary with all agent parameters
        """
        return {
            'id': agent_index,
            'capacity': self.variable_capacity,
            'base_volume': self.variable_base_volume,
            'imbalance_tolerance': self.variable_imbalance_tolerance,
            'limit_buy': self.variable_limit_buy_start + agent_index * self.variable_limit_buy_step,
            'limit_sell': self.variable_limit_sell_start + agent_index * self.variable_limit_sell_step,
            'base_forecast': self.variable_forecast_base_start + agent_index * self.variable_forecast_base_step,
            'seed': self.seed + agent_index,
        }
    
    def get_random_agent_params(self, agent_index: int) -> dict:
        """
        Get parameters for a specific Random Liquidity agent
        
        Args:
            agent_index: Index of agent (0 to n_random_liquidity_agents-1)
            
        Returns:
            Dictionary with all agent parameters
        """
        return {
            'id': 100 + agent_index,  # IDs start at 100
            'capacity': self.random_capacity,
            'limit_buy': self.random_limit_buy_start + agent_index * self.random_limit_buy_step,
            'limit_sell': self.random_limit_sell_start + agent_index * self.random_limit_sell_step,
            'min_price': self.random_min_price,
            'max_price': self.random_max_price,
            'min_volume': self.random_min_volume,
            'max_volume': self.random_max_volume,
            'n_orders': self.random_n_orders,
            'seed': self.random_seed_offset + agent_index,
            'pricing_strategy': {
                'pi_range': self.random_pi_range,
                'n_segments': self.random_n_segments,
                'n_orders': self.random_strategy_n_orders,
                'min_price': self.random_min_price,
                'max_price': self.random_max_price,
                'seed': 300 + agent_index,
            }
        }
    
    def get_thermal_agent_params(self, agent_index: int) -> dict:
        """
        Get parameters for a specific Thermal agent
        
        Args:
            agent_index: Index of agent (0 to n_thermal_agents-1)
            
        Returns:
            Dictionary with all agent parameters
        """
        marginal_cost = self.thermal_marginal_cost_start + agent_index * self.thermal_marginal_cost_step
        capacity = self.thermal_capacity_start + agent_index * self.thermal_capacity_step
        ramping_rate = self.thermal_ramping_rate_start + agent_index * self.thermal_ramping_rate_step
        switch_param = self.thermal_switch_param_start + agent_index * self.thermal_switch_param_step
        
        return {
            'id': 200 + agent_index,  # IDs start at 200
            'marginal_cost': marginal_cost,
            'capacity': capacity,
            'da_position': capacity * self.thermal_da_position_ratio,
            'base_volume': self.thermal_base_volume,
            'epsilon_price': self.thermal_epsilon_price,
            'min_stable_load': capacity * self.thermal_min_stable_load_ratio,
            'alpha': self.thermal_alpha,
            'pi_imb_plus': marginal_cost + self.thermal_imbalance_price_plus_offset,
            'pi_imb_minus': marginal_cost - self.thermal_imbalance_price_minus_offset,
            'e_imb': self.thermal_e_imb,
            'ramping_up_rate': ramping_rate,
            'ramping_down_rate': ramping_rate,
            'switch_parameter': switch_param,
            'nu_R': self.thermal_nu_r,
            'limit_buy': marginal_cost + self.thermal_limit_buy_offset,
            'limit_sell': marginal_cost - self.thermal_limit_sell_offset,
            'seed': self.thermal_seed_offset + agent_index,
            'pricing_strategy': {
                'pi_range': self.thermal_pi_range,
                'n_segments': self.thermal_n_segments,
                'n_orders': self.thermal_strategy_n_orders,
                'min_price': self.thermal_strategy_min_price,
                'max_price': self.thermal_strategy_max_price,
                'seed': self.thermal_seed_offset + 100 + agent_index,
            }
        }
    
    def print_summary(self):
        """Print a human-readable summary of the configuration"""
        print("\n" + "="*70)
        print("SIMULATION CONFIGURATION SUMMARY")
        print("="*70)
        
        print(f"\n📊 MARKET SETUP:")
        print(f"   Products:              {self.n_products} × {self.product_duration_minutes}-min")
        print(f"   Total Time:            {self.total_simulation_time_hours:.1f} hours")
        print(f"   Gate Opening:          {self.gate_open_offset_hours}h before delivery")
        print(f"   Gate Closure:          {self.gate_close_offset_minutes} min before delivery")
        print(f"   Season:                {self.season}")
        print(f"   Base DA Price:         {self.base_da_price:.2f} €/MWh")
        
        print(f"\n👥 AGENTS:")
        print(f"   Variable (RES):        {self.n_variable_agents}")
        print(f"   Random Liquidity:      {self.n_random_liquidity_agents}")
        print(f"   Thermal (Ramping):     {self.n_thermal_agents}")
        print(f"   Total:                 {self.total_agents}")
        
        print(f"\n⚙️  SIMULATION:")
        print(f"   Steps:                 {self.n_steps}")
        print(f"   Seed:                  {self.seed}")
        print(f"   Verbose:               {self.verbose}")
        
        print(f"\n💾 OUTPUT:")
        print(f"   Results Dir:           {self.results_dir}/")
        print(f"   CSV Export:            {self.export_csv}")
        if self.export_csv:
            print(f"   CSV Filename:          {self.csv_filename}")
        
        print("="*70)


# ========== PREDEFINED CONFIGURATIONS ==========

# Default Demo4 Configuration - REALISTIC MARKET SIMULATION
# Based on empirical data from German Intraday Market (EPEX SPOT)
# This is the RECOMMENDED configuration for standard simulations
DEFAULT_DEMO4_CONFIG = Demo4Config(
    # Simulation Runtime
    n_steps=1500,
    seed=42,
    verbose=True,
    
    # Market Setup - Realistic German Intraday Market
    n_products=96,
    season='winter',
    base_da_price=45.0,              # €/MWh (German average 2021-2023)
    price_volatility=5.0,             # Moderate volatility
    add_stochastic_volatility=True,
    
    # Agent Population - Balanced Mix
    n_variable_agents=10,             # Wind/Solar
    n_random_liquidity_agents=10,     # Market Makers
    n_thermal_agents=5,               # Dispatchable
    
    # Output
    results_dir="results",
    export_csv=True,
    csv_filename="demo4_simulation.csv",
)

# High Liquidity Configuration (more agents)
HIGH_LIQUIDITY_CONFIG = Demo4Config(
    n_variable_agents=20,
    n_random_liquidity_agents=30,
    n_thermal_agents=10,
)

# Fast Test Configuration (fewer steps, fewer agents)
FAST_TEST_CONFIG = Demo4Config(
    n_steps=500,
    n_variable_agents=5,
    n_random_liquidity_agents=5,
    n_thermal_agents=2,
    verbose=False,
)

# High Volatility Configuration
HIGH_VOLATILITY_CONFIG = Demo4Config(
    price_volatility=15.0,
    thermal_switch_param_start=0.3,  # Earlier switch to ramping
)

# Summer Configuration (lower prices, more solar)
SUMMER_CONFIG = Demo4Config(
    season='summer',
    base_da_price=35.0,
    variable_solar_share=0.5,
    variable_wind_share=0.5,
)


if __name__ == "__main__":
    # Demo: Show configuration summary
    print("Default Demo4 Configuration:")
    config = DEFAULT_DEMO4_CONFIG
    config.print_summary()
    
    print("\n\nExample: High Liquidity Configuration:")
    HIGH_LIQUIDITY_CONFIG.print_summary()
    
    # Example: Access specific agent parameters
    print("\n\nExample Agent Parameters:")
    print("\nVariable Agent 0:")
    print(config.get_variable_agent_params(0))
    
    print("\nRandom Agent 5:")
    print(config.get_random_agent_params(5))
    
    print("\nThermal Agent 2:")
    print(config.get_thermal_agent_params(2))