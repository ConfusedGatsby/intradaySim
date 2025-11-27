"""
Visualize Multi-Product Simulation Results

Creates plots for:
- Trading activity per product
- Volume distribution
- Agent positions over time
- Product lifecycle
"""

import csv
import matplotlib.pyplot as plt
from pathlib import Path


def load_csv(filename):
    """Load CSV file into dict of lists."""
    data = {}
    
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for key in reader.fieldnames:
            data[key] = []
        
        for row in reader:
            for key, value in row.items():
                try:
                    data[key].append(float(value))
                except ValueError:
                    data[key].append(value)
    
    return data


def plot_trading_activity(data, title, output_file):
    """Plot trading activity over time."""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(title, fontsize=16, fontweight='bold')
    
    # 1. Total trades over time
    ax = axes[0, 0]
    ax.plot(data['t'], data['n_trades'], color='blue', alpha=0.7)
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Number of Trades')
    ax.set_title('Trades per Time Step')
    ax.grid(True, alpha=0.3)
    
    # 2. Total volume over time
    ax = axes[0, 1]
    ax.plot(data['t'], data['total_volume'], color='green', alpha=0.7)
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Volume (MW)')
    ax.set_title('Trading Volume per Time Step')
    ax.grid(True, alpha=0.3)
    
    # 3. Open products over time
    ax = axes[1, 0]
    ax.plot(data['t'], data['n_open_products'], color='orange', alpha=0.7)
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Number of Open Products')
    ax.set_title('Open Products over Time')
    ax.grid(True, alpha=0.3)
    
    # 4. Orders in book over time
    ax = axes[1, 1]
    ax.plot(data['t'], data['total_orders'], color='red', alpha=0.7)
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Number of Orders')
    ax.set_title('Orders in Book over Time')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()


def plot_per_product_activity(data, title, output_file):
    """Plot activity per product."""
    
    # Detect number of products
    n_products = sum(1 for key in data.keys() if key.startswith('p') and key.endswith('_trades'))
    
    if n_products == 0:
        print("⚠️  No per-product data found")
        return
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    fig.suptitle(f"{title} - Per Product", fontsize=16, fontweight='bold')
    
    # 1. Trades per product
    ax = axes[0]
    for pid in range(min(n_products, 10)):  # Limit to 10 products for readability
        trades = data[f'p{pid}_trades']
        ax.plot(data['t'], trades, label=f'P{pid}', alpha=0.7)
    
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Number of Trades')
    ax.set_title('Trades per Product over Time')
    ax.legend(loc='upper right', ncol=5)
    ax.grid(True, alpha=0.3)
    
    # 2. Volume per product
    ax = axes[1]
    for pid in range(min(n_products, 10)):
        volume = data[f'p{pid}_volume']
        ax.plot(data['t'], volume, label=f'P{pid}', alpha=0.7)
    
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Volume (MW)')
    ax.set_title('Volume per Product over Time')
    ax.legend(loc='upper right', ncol=5)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()


def plot_cumulative_statistics(data, title, output_file):
    """Plot cumulative statistics."""
    
    # Detect number of products
    n_products = sum(1 for key in data.keys() if key.startswith('p') and key.endswith('_trades'))
    
    if n_products == 0:
        return
    
    # Calculate cumulative trades and volume per product
    cumulative_trades = []
    cumulative_volume = []
    product_labels = []
    
    for pid in range(n_products):
        total_trades = sum(data[f'p{pid}_trades'])
        total_volume = sum(data[f'p{pid}_volume'])
        
        cumulative_trades.append(total_trades)
        cumulative_volume.append(total_volume)
        product_labels.append(f'P{pid}')
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f"{title} - Cumulative Statistics", fontsize=16, fontweight='bold')
    
    # 1. Total trades per product
    ax = axes[0]
    bars = ax.bar(product_labels, cumulative_trades, color='steelblue', alpha=0.7)
    ax.set_xlabel('Product')
    ax.set_ylabel('Total Trades')
    ax.set_title('Total Trades per Product')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Rotate labels if many products
    if n_products > 10:
        ax.set_xticks(range(0, n_products, 2))
        ax.set_xticklabels([f'P{i}' for i in range(0, n_products, 2)])
    
    # 2. Total volume per product
    ax = axes[1]
    bars = ax.bar(product_labels, cumulative_volume, color='forestgreen', alpha=0.7)
    ax.set_xlabel('Product')
    ax.set_ylabel('Total Volume (MW)')
    ax.set_title('Total Volume per Product')
    ax.grid(True, alpha=0.3, axis='y')
    
    if n_products > 10:
        ax.set_xticks(range(0, n_products, 2))
        ax.set_xticklabels([f'P{i}' for i in range(0, n_products, 2)])
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()


def main():
    """Generate all plots for demo results."""
    
    print("\n" + "="*70)
    print("📊 PLOTTING MULTI-PRODUCT SIMULATION RESULTS")
    print("="*70 + "\n")
    
    results_dir = Path("results")
    plots_dir = Path("plots")
    plots_dir.mkdir(exist_ok=True)
    
    demos = [
        ("demo1_basic.csv", "Demo 1: Basic Multi-Product"),
        ("demo2_mixed.csv", "Demo 2: Mixed Agents"),
        ("demo3_many_products.csv", "Demo 3: Many Products (24h)"),
    ]
    
    for csv_file, title in demos:
        csv_path = results_dir / csv_file
        
        if not csv_path.exists():
            print(f"⚠️  Skipping {csv_file} (not found)")
            continue
        
        print(f"\n📈 Processing {csv_file}...")
        
        data = load_csv(csv_path)
        
        # Create plots
        base_name = csv_file.replace('.csv', '')
        
        plot_trading_activity(
            data, 
            title,
            plots_dir / f"{base_name}_activity.png"
        )
        
        plot_per_product_activity(
            data,
            title,
            plots_dir / f"{base_name}_per_product.png"
        )
        
        plot_cumulative_statistics(
            data,
            title,
            plots_dir / f"{base_name}_cumulative.png"
        )
    
    print("\n" + "="*70)
    print("✨ ALL PLOTS GENERATED!")
    print("="*70)
    print(f"\n📁 Plots saved to: plots/")
    print(f"\n💡 Open the PNG files to see your results!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()