"""
Demo 4: Full Day with 96 Quarterly Products (15-min granularity)

Wissenschaftlich fundierte Simulation mit:
- 96 Produkten (24h × 4 Quarterstunden)
- Realistische DA-Preise (Kremer et al. 2021)
- 10 VariableAgents mit diversen Forecasts
- 10 RandomLiquidityAgents (Shinde-konforme Pricing)
- 1500 Simulation Steps
- Erwartung: ~50,000-100,000 Trades

UPDATED: Verwendet jetzt create_quarterly_products() aus product.py!
"""

from random import Random
import os

from intraday_abm.sim.multi_product_simulation import (
    run_multi_product_simulation,
    print_simulation_summary,
)
from intraday_abm.core.product import (
    create_quarterly_products,
    print_quarterly_products_summary
)
from intraday_abm.core.types import MultiProductPrivateInfo
from intraday_abm.agents.variable import VariableAgent
from intraday_abm.agents.random_liquidity import RandomLiquidityAgent
from intraday_abm.agents.pricing_strategies import NaivePricingStrategy


def demo_full_day_quarterly():
    """
    Demo 4: Full Day mit 96 Quarterly Products (15-min).
    
    Setup:
    - 96 Produkte (H00Q1 - H23Q4)
    - Realistische DA-Preise (Winter-Szenario)
    - 10 VariableAgents (Wind/Solar mit diversen Forecasts)
    - 10 RandomLiquidityAgents (Shinde-Pricing, breite Limits)
    - 1500 Steps (ausreichend für alle 96 Produkte)
    
    Erwartete Resultate:
    - ~50,000-100,000 Trades
    - ~200,000-400,000 MW Volumen
    - Peak bei ~8-12 offenen Produkten
    - Realistische Preisverteilung
    """
    print("\n" + "="*70)
    print("DEMO 4: FULL DAY QUARTERLY (96 × 15-MIN PRODUCTS)")
    print("="*70)
    
    # Create 96 quarterly products with realistic DA prices
    # NOW USING INTEGRATED FUNCTION FROM product.py!
    products = create_quarterly_products(
        n_hours=24,
        start_time=1440,  # Day 2
        gate_open_offset_hours=24,
        gate_close_offset_minutes=5,
        season='winter',  # Winter scenario (higher peak prices)
        base_da_price=45.0,
        price_volatility=5.0,
        add_stochastic_volatility=True,
        seed=42
    )
    
    print_quarterly_products_summary(products)
    
    agents = []
    
    # --- 10 Multi-Product Variable Agents (Wind/Solar) ---
    print(f"\n👥 Creating 10 VariableAgents (Diverse Forecasts):")
    for i in range(10):
        # Diverse Limit Prices
        limit_buy = 55.0 + i * 3.0    # 55, 58, 61, ..., 82 €/MWh
        limit_sell = 45.0 - i * 1.5   # 45, 43.5, 42, ..., 31.5 €/MWh
        
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=150.0,  # Larger capacity for 96 products
            limit_buy=limit_buy,
            limit_sell=limit_sell
        )
        
        # Create diverse forecast patterns
        # Simulate realistic wind/solar patterns
        base_forecast = 40.0 + i * 10.0  # 40, 50, ..., 130 MW
        
        for pid in range(96):
            hour = pid // 4
            quarter = pid % 4
            
            # Solar pattern (higher during day, zero at night)
            if 6 <= hour < 20:
                # Day time
                solar_factor = 1.0 + 0.5 * ((hour - 13) / 7.0) ** 2  # Peak at noon
                solar_component = base_forecast * 0.3 * solar_factor
            else:
                solar_component = 0.0
            
            # Wind pattern (more stable, slight day/night variation)
            wind_component = base_forecast * 0.7 * (1.0 + 0.2 * (hour / 24.0))
            
            # Quarterly variation (small)
            quarterly_var = 5.0 * (quarter / 4.0 - 0.5)
            
            forecast = solar_component + wind_component + quarterly_var
            priv_info.forecasts[pid] = max(10.0, forecast)
        
        agent = VariableAgent(
            id=i,
            private_info=priv_info,
            rng=Random(42 + i),
            base_forecast=base_forecast,
            base_volume=15.0,
            imbalance_tolerance=5.0
        )
        
        # Show sample forecasts
        sample_forecasts = [priv_info.forecasts[pid] for pid in [0, 24, 48, 72]]  # H00, H06, H12, H18
        print(f"   Agent {agent.id}: Limits [Buy: {limit_buy:.1f}, Sell: {limit_sell:.1f}], "
              f"Forecasts [H00: {sample_forecasts[0]:.0f}, H06: {sample_forecasts[1]:.0f}, "
              f"H12: {sample_forecasts[2]:.0f}, H18: {sample_forecasts[3]:.0f}] MW")
        
        agents.append(agent)
    
    # --- 10 Multi-Product RandomLiquidity Agents ---
    print(f"\n👥 Creating 10 RandomLiquidityAgents (Shinde-Pricing):")
    for i in range(10):
        # Wide Limits for Liquidity Providers
        limit_buy = 75.0 + i * 3.0    # 75, 78, 81, ..., 102 €/MWh
        limit_sell = 25.0 - i * 1.0   # 25, 24, 23, ..., 16 €/MWh
        
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=400.0,  # Large capacity for liquidity
            limit_buy=limit_buy,
            limit_sell=limit_sell
        )
        
        agent = RandomLiquidityAgent(
            id=100 + i,
            private_info=priv_info,
            rng=Random(200 + i),
            min_price=15.0,   # Wide absolute bounds
            max_price=120.0,
            min_volume=3.0,
            max_volume=12.0,
            n_orders=7  # More orders for more products
        )
        
        # SHINDE-KONFORME STRATEGY
        agent.pricing_strategy = NaivePricingStrategy(
            rng=Random(300 + i),
            pi_range=8.0,     # Larger range for 96 products
            n_segments=15,
            n_orders=7,
            min_price=15.0,
            max_price=120.0
        )
        
        print(f"   Agent {agent.id}: Limits [Buy: {limit_buy:.1f}, Sell: {limit_sell:.1f}]")
        agents.append(agent)
    
    print(f"\n📊 Total Agents: {len(agents)}")
    print(f"   VariableAgents:       10")
    print(f"   RandomLiquidityAgents: 10")
    
    # Run simulation (NO debug for performance with 96 products)
    print(f"\n▶️  Running simulation (1500 steps)...")
    print(f"   ⚠️  Debug disabled for performance (96 products = high volume)")
    print(f"   💡 Expected: ~50,000-100,000 Trades")
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=1500,
        seed=42,
        verbose=True  # Keep progress output
    )
    
    # Print summary
    print_simulation_summary(log, agent_logs, mo)
    
    # Additional 96-product statistics
    print(f"\n" + "="*70)
    print("96-PRODUCT DETAILED STATISTICS")
    print("="*70)
    
    # Per-Hour aggregation
    print(f"\n📊 HOURLY AGGREGATED STATISTICS:")
    for hour in [0, 6, 12, 18, 23]:
        hour_products = list(range(hour * 4, (hour + 1) * 4))
        hour_trades = sum(log[f"p{pid}_trades"][-1] for pid in hour_products if pid < 96)
        hour_volume = sum(log[f"p{pid}_volume"][-1] for pid in hour_products if pid < 96)
        
        # Average DA price for this hour
        hour_da_prices = [products[pid].da_price for pid in hour_products if pid < 96]
        avg_da = sum(hour_da_prices) / len(hour_da_prices) if hour_da_prices else 0.0
        
        print(f"   H{hour:02d} (Q1-Q4): {hour_trades:5d} trades, {hour_volume:8.0f} MW, "
              f"Avg DA: {avg_da:.2f} €/MWh")
    
    # Peak vs Off-Peak
    peak_products = list(range(8 * 4, 20 * 4))  # H08-H19
    off_peak_products = list(range(0, 8 * 4)) + list(range(20 * 4, 24 * 4))
    
    peak_trades = sum(log[f"p{pid}_trades"][-1] for pid in peak_products)
    off_peak_trades = sum(log[f"p{pid}_trades"][-1] for pid in off_peak_products)
    
    total_trades = log['n_trades'][-1]
    if total_trades > 0:
        print(f"\n⚡ PEAK vs OFF-PEAK:")
        print(f"   Peak (H08-H19):     {peak_trades:6d} trades ({peak_trades/total_trades*100:.1f}%)")
        print(f"   Off-Peak (H00-H07, H20-H23): {off_peak_trades:6d} trades ({off_peak_trades/total_trades*100:.1f}%)")
    
    # Quarterly pattern
    print(f"\n🕐 QUARTERLY PATTERN (Sample Hour H12):")
    for q in range(4):
        pid = 12 * 4 + q
        trades = log[f"p{pid}_trades"][-1]
        volume = log[f"p{pid}_volume"][-1]
        print(f"   {products[pid].name}: {trades:4d} trades, {volume:6.0f} MW, DA: {products[pid].da_price:.2f} €/MWh")
    
    return log, agent_logs, mo, products


def export_quarterly_results_to_csv(log, products, filename="demo4_quarterly_96products.csv"):
    """
    Export 96-product simulation results to CSV.
    
    Args:
        log: Market log from simulation
        products: List of Product instances
        filename: Output filename
    """
    import csv
    
    print(f"\n💾 Exporting 96-product results to {filename}...")
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ["t", "n_trades", "total_volume", "n_open_products", "total_orders"]
        
        # Add product columns (96 products!)
        for pid in range(96):
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
            
            for pid in range(96):
                row.extend([
                    log[f"p{pid}_trades"][i],
                    log[f"p{pid}_volume"][i],
                    log[f"p{pid}_orders"][i]
                ])
            
            writer.writerow(row)
    
    print(f"✅ Exported {len(log['t'])} rows × {len(header)} columns to {filename}")
    print(f"   File size: ~{len(log['t']) * 96 * 3 * 8 / 1024 / 1024:.1f} MB (estimated)")


def main():
    """Run Demo 4 with 96 quarterly products."""
    
    print("\n" + "🚀"*35)
    print("   96-PRODUCT QUARTERLY SIMULATION DEMO")
    print("   (15-MIN GRANULARITY - SCIENTIFIC)")
    print("🚀"*35)
    
    # Run Demo 4
    log, agent_logs, mo, products = demo_full_day_quarterly()
    
    # Export results
    os.makedirs("results", exist_ok=True)
    export_quarterly_results_to_csv(log, products, "results/demo4_quarterly_96products.csv")
    
    print("\n" + "="*70)
    print("✨ DEMO 4 COMPLETED!")
    print("="*70)
    print(f"\n📁 Results saved to:")
    print(f"   - results/demo4_quarterly_96products.csv")
    print(f"\n🎉 96-Product Simulation erfolgreich mit realistischen DA-Preisen!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()