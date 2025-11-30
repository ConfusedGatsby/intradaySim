"""
Demo 4: 96-Product Quarterly Simulation - Production Version

This is the PRODUCTION version of Demo4 with:
- Automatic use of realistic default configuration
- Structured logging (no more print statements!)
- Clean, professional output
- Easy to run without configuration

Usage:
    # Simple - just run with defaults
    python Demo4.py
    
    # Advanced - customize configuration
    from Demo4 import run_demo4
    from intraday_abm.config_params.demo4_config import Demo4Config
    
    custom_config = Demo4Config(n_variable_agents=20)
    run_demo4(custom_config)
"""

import time
import os
from pathlib import Path
from typing import Optional

import os
from random import Random
from typing import List, Dict

from intraday_abm.sim.multi_product_simulation import run_multi_product_simulation
from intraday_abm.core.product import create_quarterly_products, print_quarterly_products_summary
from intraday_abm.config_params.demo4_config import DEFAULT_DEMO4_CONFIG, Demo4Config
from intraday_abm.utils.logging import setup_logger, SimulationLogger

# Agent imports
from intraday_abm.core.types import MultiProductPrivateInfo
from intraday_abm.agents.variable import VariableAgent
from intraday_abm.agents.random_liquidity import RandomLiquidityAgent
from intraday_abm.agents.dispatchable import DispatchableAgent
from intraday_abm.agents.pricing_strategies import NaivePricingStrategy


def setup_logging_from_config(config: Demo4Config):
    """
    Setup logging based on configuration.
    
    Args:
        config: Demo4Config instance
        
    Returns:
        Tuple of (base_logger, sim_logger)
    """
    if not config.enable_logging:
        # Minimal logging if disabled
        import logging
        logging.basicConfig(level=logging.WARNING)
        logger = logging.getLogger('demo4')
        return logger, None
    
    # Create logs directory
    log_dir = Path(config.results_dir) / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logger
    log_file = log_dir / config.log_filename if config.log_to_file else None
    
    logger = setup_logger(
        name='demo4',
        log_file=str(log_file) if log_file else None,
        level=config.log_level,
        log_to_console=config.log_to_console,
        use_colors=True
    )
    
    # Create high-level simulation logger
    sim_logger = SimulationLogger(logger)
    
    return logger, sim_logger


def create_variable_agents(config: Demo4Config, products: List) -> List[VariableAgent]:
    """Create Variable Agents (Wind/Solar) from configuration."""
    agents = []
    
    print(f"\n👥 Creating {config.n_variable_agents} VariableAgents (Diverse Forecasts):")
    
    for i in range(config.n_variable_agents):
        params = config.get_variable_agent_params(i)
        
        # Create Multi-Product PrivateInfo
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=params['capacity'],
            limit_buy=params['limit_buy'],
            limit_sell=params['limit_sell']
        )
        
        # Create diverse forecast patterns (Solar + Wind)
        for pid in range(len(products)):
            hour = pid // 4
            
            # Solar pattern (higher during day, zero at night)
            if 6 <= hour < 20:
                solar_factor = 1.0 + 0.5 * ((hour - 13) / 7.0) ** 2
                solar_component = params['base_forecast'] * config.variable_solar_share * solar_factor
            else:
                solar_component = 0.0
            
            # Wind pattern (more stable)
            wind_component = params['base_forecast'] * config.variable_wind_share * (1.0 + 0.2 * (hour / 24.0))
            
            forecast = solar_component + wind_component
            priv_info.forecasts[pid] = max(10.0, forecast)
        
        # Create agent
        agent = VariableAgent(
            id=params['id'],
            private_info=priv_info,
            rng=Random(params['seed']),
            base_forecast=params['base_forecast'],
            base_volume=params['base_volume'],
            imbalance_tolerance=params['imbalance_tolerance']
        )
        
        # Show sample forecasts
        sample_forecasts = [priv_info.forecasts[pid] for pid in [0, 24, 48, 72]]
        print(f"   Agent {agent.id}: "
              f"Limits [Buy: {params['limit_buy']:.1f}, Sell: {params['limit_sell']:.1f}], "
              f"Forecasts [H00: {sample_forecasts[0]:.0f}, H06: {sample_forecasts[1]:.0f}, "
              f"H12: {sample_forecasts[2]:.0f}, H18: {sample_forecasts[3]:.0f}] MW")
        
        agents.append(agent)
    
    return agents


def create_random_liquidity_agents(config: Demo4Config, products: List) -> List[RandomLiquidityAgent]:
    """Create Random Liquidity Agents (Market Makers) from configuration."""
    agents = []
    
    print(f"\n👥 Creating {config.n_random_liquidity_agents} RandomLiquidityAgents (Shinde-Pricing):")
    
    for i in range(config.n_random_liquidity_agents):
        params = config.get_random_agent_params(i)
        
        # Create Multi-Product PrivateInfo
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=params['capacity'],
            limit_buy=params['limit_buy'],
            limit_sell=params['limit_sell']
        )
        
        # Create agent
        agent = RandomLiquidityAgent(
            id=params['id'],
            private_info=priv_info,
            rng=Random(params['seed']),
            min_price=params['min_price'],
            max_price=params['max_price'],
            min_volume=params['min_volume'],
            max_volume=params['max_volume'],
            n_orders=params['n_orders']
        )
        
        # Assign Shinde-compliant Naive Pricing Strategy
        ps_params = params['pricing_strategy']
        agent.pricing_strategy = NaivePricingStrategy(
            rng=Random(ps_params['seed']),
            pi_range=ps_params['pi_range'],
            n_segments=ps_params['n_segments'],
            n_orders=ps_params['n_orders'],
            min_price=ps_params['min_price'],
            max_price=ps_params['max_price']
        )
        
        print(f"   Agent {agent.id}: "
              f"Limits [Buy: {params['limit_buy']:.1f}, Sell: {params['limit_sell']:.1f}]")
        
        agents.append(agent)
    
    return agents


def create_thermal_agents(config: Demo4Config, products: List) -> List[DispatchableAgent]:
    """Create Thermal Agents (Dispatchable with Ramping) from configuration."""
    agents = []
    
    print(f"\n🏭 Creating {config.n_thermal_agents} ThermalAgents (Dispatchable with Ramping):")
    
    for i in range(config.n_thermal_agents):
        params = config.get_thermal_agent_params(i)
        
        # Create Multi-Product PrivateInfo
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=params['capacity'],
            initial_da_position=params['da_position'],
        )
        
        # Initialize limit prices
        priv_info.limit_buy_initial = params['limit_buy']
        priv_info.limit_sell_initial = params['limit_sell']
        priv_info.limit_buy = params['limit_buy']
        priv_info.limit_sell = params['limit_sell']
        
        # Create agent
        agent = DispatchableAgent(
            id=params['id'],
            private_info=priv_info,
            rng=Random(params['seed']),
            marginal_cost=params['marginal_cost'],
            base_volume=params['base_volume'],
            epsilon_price=params['epsilon_price'],
            min_stable_load=params['min_stable_load'],
            alpha=params['alpha'],
            pi_imb_plus=params['pi_imb_plus'],
            pi_imb_minus=params['pi_imb_minus'],
            e_imb=params['e_imb'],
            ramping_up_rate=params['ramping_up_rate'],
            ramping_down_rate=params['ramping_down_rate'],
            switch_parameter=params['switch_parameter'],
            nu_R=params['nu_R']
        )
        
        # Assign pricing strategy
        ps_params = params['pricing_strategy']
        agent.pricing_strategy = NaivePricingStrategy(
            rng=Random(ps_params['seed']),
            pi_range=ps_params['pi_range'],
            n_segments=ps_params['n_segments'],
            n_orders=ps_params['n_orders'],
            min_price=ps_params['min_price'],
            max_price=ps_params['max_price']
        )
        
        print(f"   Agent {agent.id}: "
              f"MC={params['marginal_cost']} €/MWh, "
              f"Cap={params['capacity']} MW, "
              f"Ramp={params['ramping_up_rate']} MW/h, "
              f"Switch={params['switch_parameter']*100:.0f}%, "
              f"MinLoad={params['min_stable_load']} MW")
        
        agents.append(agent)
    
    return agents


def print_simulation_summary(log: Dict, agent_logs: Dict, agents: List, products: List, config: Demo4Config):
    """Print scientific summary of simulation results."""
    print("\n" + "="*70)
    print("SIMULATION RESULTS - SCIENTIFIC SUMMARY")
    print("="*70)
    
    # Market Overview
    print(f"\n{'─'*70}")
    print("1. MARKET OVERVIEW")
    print(f"{'─'*70}")
    
    total_trades = sum(log["n_trades"])
    total_volume = sum(log["total_volume"])
    avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
    n_steps = len(log["t"])
    
    print(f"\nAggregate Statistics:")
    print(f"  Total Trades:        {total_trades:>10,}")
    print(f"  Total Volume:        {total_volume:>10,.1f} MW")
    print(f"  Average Trade Size:  {avg_trade_size:>10.2f} MW")
    print(f"  Trades per Step:     {total_trades/n_steps:>10.2f}")
    print(f"  Simulation Steps:    {n_steps:>10,}")
    
    # Trading intensity
    steps_with_trades = sum(1 for n in log["n_trades"] if n > 0)
    market_activity = steps_with_trades / n_steps * 100 if n_steps > 0 else 0
    
    print(f"\nMarket Efficiency:")
    print(f"  Steps with Trades:   {steps_with_trades:>10,} ({market_activity:.1f}%)")
    print(f"  Max Open Products:   {max(log['n_open_products']):>10}")
    print(f"  Avg Open Products:   {sum(log['n_open_products'])/n_steps:>10.1f}")
    
    # Agent Performance Summary
    print(f"\n{'─'*70}")
    print("2. AGENT PERFORMANCE SUMMARY")
    print(f"{'─'*70}")
    
    # Group by type
    variable_agents = [a for a in agents if isinstance(a, VariableAgent)]
    random_agents = [a for a in agents if isinstance(a, RandomLiquidityAgent)]
    thermal_agents = [a for a in agents if isinstance(a, DispatchableAgent)]
    
    if variable_agents:
        var_revenues = [agent_logs[a.id]['total_revenue'][-1] if agent_logs[a.id]['total_revenue'] else 0.0 
                       for a in variable_agents]
        print(f"\nVariable Agents (n={len(variable_agents)}):")
        print(f"  Total Revenue:       {sum(var_revenues):>10,.0f} €")
        print(f"  Avg Revenue:         {sum(var_revenues)/len(var_revenues):>10,.0f} €")
        print(f"  Max Revenue:         {max(var_revenues):>10,.0f} €")
    
    if random_agents:
        rand_revenues = [agent_logs[a.id]['total_revenue'][-1] if agent_logs[a.id]['total_revenue'] else 0.0
                        for a in random_agents]
        print(f"\nRandom Liquidity Agents (n={len(random_agents)}):")
        print(f"  Total Revenue:       {sum(rand_revenues):>10,.0f} €")
        print(f"  Avg Revenue:         {sum(rand_revenues)/len(rand_revenues):>10,.0f} €")
    
    if thermal_agents:
        therm_revenues = [agent_logs[a.id]['total_revenue'][-1] if agent_logs[a.id]['total_revenue'] else 0.0
                         for a in thermal_agents]
        print(f"\nThermal Agents (n={len(thermal_agents)}):")
        print(f"  Total Revenue:       {sum(therm_revenues):>10,.0f} €")
        print(f"  Avg Revenue:         {sum(therm_revenues)/len(therm_revenues):>10,.0f} €")
        print(f"  Max Revenue:         {max(therm_revenues):>10,.0f} €")
    
    print("\n" + "="*70)


def export_results(log: Dict, products: List, config: Demo4Config):
    """Export results to CSV if configured."""
    if not config.export_csv:
        return
    
    import csv
    
    os.makedirs(config.results_dir, exist_ok=True)
    filepath = os.path.join(config.results_dir, config.csv_filename)
    
    print(f"\n💾 Exporting results to {filepath}...")
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ["t", "n_trades", "total_volume", "n_open_products", "total_orders"]
        for pid in range(len(products)):
            header.extend([f"p{pid}_trades", f"p{pid}_volume", f"p{pid}_orders"])
        writer.writerow(header)
        
        # Data
        for i in range(len(log["t"])):
            row = [
                log["t"][i],
                log["n_trades"][i],
                log["total_volume"][i],
                log["n_open_products"][i],
                log["total_orders"][i]
            ]
            
            for pid in range(len(products)):
                row.extend([
                    log[f"p{pid}_trades"][i],
                    log[f"p{pid}_volume"][i],
                    log[f"p{pid}_orders"][i]
                ])
            
            writer.writerow(row)
    
    print(f"✅ Exported {len(log['t'])} rows to {filepath}")


def setup_logging_from_config(config: Demo4Config):
    """
    Setup logging based on configuration.
    
    Args:
        config: Demo4Config instance
        
    Returns:
        Tuple of (base_logger, sim_logger)
    """
    if not config.enable_logging:
        # Minimal logging if disabled
        import logging
        logging.basicConfig(level=logging.WARNING)
        logger = logging.getLogger('demo4')
        return logger, None
    
    # Create logs directory
    log_dir = Path(config.results_dir) / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logger
    log_file = log_dir / config.log_filename if config.log_to_file else None
    
    logger = setup_logger(
        name='demo4',
        log_file=str(log_file) if log_file else None,
        level=config.log_level,
        log_to_console=config.log_to_console,
        use_colors=True
    )
    
    # Create high-level simulation logger
    sim_logger = SimulationLogger(logger)
    
    return logger, sim_logger


def run_demo4(config: Optional[Demo4Config] = None):
    """
    Run Demo 4 simulation with configuration.
    
    Args:
        config: Demo4Config instance (uses DEFAULT_DEMO4_CONFIG if None)
        
    Returns:
        Tuple of (log, agent_logs, market_operator, products)
    """
    
    # Use default config if none provided
    if config is None:
        config = DEFAULT_DEMO4_CONFIG
    
    # Setup logging
    logger, sim_logger = setup_logging_from_config(config)
    
    # Print banner
    print("\n" + "🚀"*35)
    print("   96-PRODUCT INTRADAY MARKET SIMULATION")
    print("🚀"*35)
    
    # Log configuration
    if sim_logger:
        logger.info("="*70)
        logger.info("DEMO4 SIMULATION CONFIGURATION")
        logger.info("="*70)
        logger.info("Market: %d products × %d min, Season: %s, Base DA: %.2f €/MWh",
                   config.n_products, config.product_duration_minutes, 
                   config.season, config.base_da_price)
        logger.info("Agents: %d Variable, %d Random Liquidity, %d Thermal (Total: %d)",
                   config.n_variable_agents, config.n_random_liquidity_agents,
                   config.n_thermal_agents, config.total_agents)
        n_steps_log = config.n_steps if config.n_steps is not None else "Auto (calculated from products)"
        logger.info("Simulation: %s steps, Seed: %d", n_steps_log, config.seed)
        logger.info("Output: %s, CSV Export: %s", config.results_dir, config.export_csv)
        logger.info("="*70)
    else:
        # Fallback to print if logging disabled
        config.print_summary()
    
    # Create products
    if logger:
        logger.info("Creating %d quarterly products...", config.n_products)
    
    products = create_quarterly_products(
        n_hours=24,
        start_time=config.start_time_minutes,
        gate_open_offset_hours=config.gate_open_offset_hours,
        gate_close_offset_minutes=config.gate_close_offset_minutes,
        season=config.season,
        base_da_price=config.base_da_price,
        price_volatility=config.price_volatility,
        add_stochastic_volatility=config.add_stochastic_volatility,
        seed=config.seed
    )
    
    # Print product summary to console (always visible)
    print("\n" + "="*70)
    print("QUARTERLY PRODUCTS SUMMARY")
    print("="*70)
    print_quarterly_products_summary(products)
    
    # ========== CALCULATE N_STEPS FROM PRODUCTS (OPTION B) ==========
    # If n_steps is None, calculate it to ensure simulation runs until
    # ALL product gates are closed (required for complete settlement)
    if config.n_steps is None:
        n_steps = config.calculate_n_steps_from_products(products)
        if logger:
            logger.info("Auto-calculated n_steps from products: %d", n_steps)
        print(f"\n⏰ Simulation Timeline:")
        print(f"   Gate Opening:      t=0")
        print(f"   Last Gate Closure: t={n_steps - 1}")
        print(f"   Total Steps:       {n_steps} (auto-calculated)")
        print(f"   Expected Duration: ~{n_steps / 60:.1f} hours of trading")
    else:
        n_steps = config.n_steps
        if logger:
            logger.info("Using configured n_steps: %d", n_steps)
        print(f"\n⏰ Simulation Timeline:")
        print(f"   Total Steps:       {n_steps} (configured)")
    
    # Create agents
    if logger:
        logger.info("Creating agents...")
    
    print("\n" + "="*70)
    print("CREATING AGENTS")
    print("="*70)
    
    agents = []
    
    # Variable Agents
    variable_agents = create_variable_agents(config, products)
    agents.extend(variable_agents)
    if logger:
        logger.info("Created %d Variable Agents", len(variable_agents))
    
    # Random Liquidity Agents
    random_agents = create_random_liquidity_agents(config, products)
    agents.extend(random_agents)
    if logger:
        logger.info("Created %d Random Liquidity Agents", len(random_agents))
    
    # Thermal Agents
    thermal_agents = create_thermal_agents(config, products)
    agents.extend(thermal_agents)
    if logger:
        logger.info("Created %d Thermal Agents", len(thermal_agents))
    
    print(f"\n📊 Total Agents: {len(agents)}")
    print(f"   Variable:        {config.n_variable_agents}")
    print(f"   Random Liq:      {config.n_random_liquidity_agents}")
    print(f"   Thermal:         {config.n_thermal_agents}")
    
    # Run simulation
    print("\n" + "="*70)
    print("RUNNING SIMULATION")
    print("="*70)
    
    if sim_logger:
        sim_logger.simulation_start(n_steps, len(agents), len(products))
    
    start_time = time.time()
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=n_steps,  # Use calculated n_steps
        seed=config.seed,
        verbose=config.verbose
    )
    
    elapsed_time = time.time() - start_time
    
    # Log completion
    total_trades = sum(log["n_trades"])
    total_volume = sum(log["total_volume"])
    
    if sim_logger:
        sim_logger.simulation_end(total_trades, total_volume, elapsed_time)
    
    if logger:
        logger.info("="*70)
        logger.info("Performance: %.2f seconds, %.1f trades/second", 
                   elapsed_time, total_trades/elapsed_time if elapsed_time > 0 else 0)
        logger.info("="*70)
    
    # Print results
    print("\n" + "="*70)
    print("SIMULATION RESULTS")
    print("="*70)
    print_simulation_summary(log, agent_logs, agents, products, config)
    
    # Export results
    if config.export_csv:
        if logger:
            logger.info("Exporting results to CSV...")
        export_results(log, products, config)
    
    # Final status
    print("\n" + "="*70)
    print("✅ SIMULATION COMPLETED SUCCESSFULLY")
    print("="*70)
    
    if config.log_to_file:
        log_path = Path(config.results_dir) / 'logs' / config.log_filename
        print(f"\n📝 Detailed log: {log_path}")
    
    if config.export_csv:
        csv_path = Path(config.results_dir) / config.csv_filename
        print(f"📊 Results CSV: {csv_path}")
    
    print()
    
    return log, agent_logs, mo, products


def main():
    """Main entry point - runs Demo4 with default configuration"""
    
    # Simply run with defaults - that's it!
    log, agent_logs, mo, products = run_demo4()
    
    # Optional: Do something with results
    # analyze_results(log, agent_logs)
    # create_plots(log)
    # etc.


if __name__ == "__main__":
    main()