"""
Comprehensive Plotting Script for 96-Product Intraday Simulation

Creates multi-level visualization:
- Individual product plots (96 products)
- Hourly aggregations (24 hours)
- Time-of-day clusters (4 periods)
- Summary dashboards

Usage:
    python plot_96_products.py results/demo4_quarterly_96products.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
from typing import Dict, List, Tuple
from multiprocessing import Pool
import warnings
warnings.filterwarnings('ignore')

# Styling
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Color scheme
COLORS = {
    'midprice': '#2E86AB',
    'best_bid': '#06A77D',
    'best_ask': '#D62246',
    'da_price': '#000000',
    'spread': '#A9A9A9',
    'volume': '#F77F00',
    'gate_open': '#06A77D',
    'gate_close': '#D62246',
}


class ProductPlotter:
    """Handles all plotting operations for 96-product simulation."""
    
    def __init__(self, csv_file: str, output_base: str = "results/plots"):
        """
        Initialize plotter.
        
        Args:
            csv_file: Path to CSV file with simulation results
            output_base: Base directory for output plots
        """
        self.csv_file = csv_file
        self.output_base = Path(output_base)
        self.df = None
        self.products_info = {}
        
        # Load data
        self._load_data()
        
    def _load_data(self):
        """Load and preprocess CSV data."""
        print("📊 Loading CSV data...")
        self.df = pd.read_csv(self.csv_file)
        print(f"✅ Loaded {len(self.df)} rows")
        
        # Extract product names and info from CSV
        # Assuming columns: t, n_trades, total_volume, n_open_products, total_orders,
        #                   p0_trades, p0_volume, p0_orders, p1_trades, ...
        
    def get_product_name(self, pid: int) -> str:
        """Convert product ID to name (e.g., 0 -> H00Q1)."""
        hour = pid // 4
        quarter = pid % 4 + 1
        return f"H{hour:02d}Q{quarter}"
    
    def extract_product_data(self, pid: int) -> pd.DataFrame:
        """
        Extract data for specific product from main dataframe.
        
        Args:
            pid: Product ID (0-95)
            
        Returns:
            DataFrame with product-specific data
        """
        # Extract columns for this product
        trades_col = f"p{pid}_trades"
        volume_col = f"p{pid}_volume"
        orders_col = f"p{pid}_orders"
        
        if trades_col not in self.df.columns:
            raise ValueError(f"Product {pid} data not found in CSV")
        
        product_df = pd.DataFrame({
            't': self.df['t'],
            'trades': self.df[trades_col],
            'volume': self.df[volume_col],
            'orders': self.df[orders_col],
        })
        
        # Add cumulative volume
        product_df['cumulative_volume'] = product_df['volume'].cumsum()
        
        # Add cumulative trades
        product_df['cumulative_trades'] = product_df['trades'].cumsum()
        
        return product_df
    
    def plot_product_activity(self, pid: int, output_dir: Path):
        """
        Create activity plot for a single product.
        
        Shows:
        - Trades per step
        - Cumulative volume
        - Number of orders
        
        Args:
            pid: Product ID
            output_dir: Output directory
        """
        data = self.extract_product_data(pid)
        product_name = self.get_product_name(pid)
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.suptitle(f'{product_name} - Trading Activity', fontsize=16, fontweight='bold')
        
        # Subplot 1: Trades per Step
        ax1 = axes[0]
        ax1.bar(data['t'], data['trades'], color=COLORS['volume'], alpha=0.7, width=1)
        ax1.set_ylabel('Trades per Step', fontsize=12)
        ax1.set_title('Trade Frequency', fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # Add average line
        avg_trades = data['trades'].mean()
        ax1.axhline(avg_trades, color='red', linestyle='--', 
                   label=f'Average: {avg_trades:.2f}', linewidth=2)
        ax1.legend()
        
        # Subplot 2: Cumulative Volume
        ax2 = axes[1]
        ax2.plot(data['t'], data['cumulative_volume'], 
                color=COLORS['midprice'], linewidth=2)
        ax2.fill_between(data['t'], 0, data['cumulative_volume'], 
                        alpha=0.3, color=COLORS['midprice'])
        ax2.set_ylabel('Cumulative Volume (MW)', fontsize=12)
        ax2.set_title('Total Traded Volume', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # Add final volume annotation
        final_volume = data['cumulative_volume'].iloc[-1]
        ax2.text(0.02, 0.98, f'Total: {final_volume:.1f} MW', 
                transform=ax2.transAxes, fontsize=11,
                verticalalignment='top', bbox=dict(boxstyle='round', 
                facecolor='wheat', alpha=0.5))
        
        # Subplot 3: Orders in Book
        ax3 = axes[2]
        ax3.plot(data['t'], data['orders'], color=COLORS['best_bid'], linewidth=1.5)
        ax3.fill_between(data['t'], 0, data['orders'], 
                        alpha=0.2, color=COLORS['best_bid'])
        ax3.set_xlabel('Time Step', fontsize=12)
        ax3.set_ylabel('Number of Orders', fontsize=12)
        ax3.set_title('Orderbook Depth', fontsize=12)
        ax3.grid(True, alpha=0.3)
        
        # Add max orders annotation
        max_orders = data['orders'].max()
        max_idx = data['orders'].idxmax()
        ax3.annotate(f'Max: {max_orders}', 
                    xy=(data.loc[max_idx, 't'], max_orders),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        plt.tight_layout()
        output_file = output_dir / 'activity_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def plot_product_statistics(self, pid: int, output_dir: Path):
        """
        Create statistics summary for a single product.
        
        Args:
            pid: Product ID
            output_dir: Output directory
        """
        data = self.extract_product_data(pid)
        product_name = self.get_product_name(pid)
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f'{product_name} - Statistical Summary', fontsize=16, fontweight='bold')
        
        # Subplot 1: Trade Size Distribution
        ax1 = axes[0, 0]
        trade_sizes = data[data['volume'] > 0]['volume']
        if len(trade_sizes) > 0:
            ax1.hist(trade_sizes, bins=30, color=COLORS['volume'], alpha=0.7, edgecolor='black')
            ax1.axvline(trade_sizes.mean(), color='red', linestyle='--', 
                       label=f'Mean: {trade_sizes.mean():.2f} MW', linewidth=2)
            ax1.set_xlabel('Trade Size (MW)', fontsize=11)
            ax1.set_ylabel('Frequency', fontsize=11)
            ax1.set_title('Trade Size Distribution', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        else:
            ax1.text(0.5, 0.5, 'No Trades', ha='center', va='center', 
                    transform=ax1.transAxes, fontsize=14)
        
        # Subplot 2: Trading Activity Timeline
        ax2 = axes[0, 1]
        # Create bins for activity
        active_steps = data[data['trades'] > 0]['t']
        if len(active_steps) > 0:
            ax2.scatter(active_steps, np.ones(len(active_steps)), 
                       c=COLORS['best_bid'], alpha=0.5, s=10)
            ax2.set_xlabel('Time Step', fontsize=11)
            ax2.set_ylabel('Active', fontsize=11)
            ax2.set_title(f'Activity Timeline ({len(active_steps)} active steps)', fontsize=12)
            ax2.set_ylim(0.5, 1.5)
            ax2.set_yticks([])
            ax2.grid(True, alpha=0.3, axis='x')
        else:
            ax2.text(0.5, 0.5, 'No Active Steps', ha='center', va='center',
                    transform=ax2.transAxes, fontsize=14)
        
        # Subplot 3: Statistics Table
        ax3 = axes[1, 0]
        ax3.axis('off')
        
        stats = {
            'Total Trades': f"{data['cumulative_trades'].iloc[-1]:.0f}",
            'Total Volume': f"{data['cumulative_volume'].iloc[-1]:.1f} MW",
            'Avg Trade Size': f"{trade_sizes.mean():.2f} MW" if len(trade_sizes) > 0 else "N/A",
            'Max Orders': f"{data['orders'].max():.0f}",
            'Avg Orders': f"{data['orders'].mean():.1f}",
            'Active Steps': f"{len(active_steps):.0f}",
            'Activity Rate': f"{len(active_steps)/len(data)*100:.1f}%",
        }
        
        table_data = [[k, v] for k, v in stats.items()]
        table = ax3.table(cellText=table_data, colLabels=['Metric', 'Value'],
                         cellLoc='left', loc='center',
                         colWidths=[0.6, 0.4])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # Color header
        for i in range(2):
            table[(0, i)].set_facecolor(COLORS['midprice'])
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        ax3.set_title('Summary Statistics', fontsize=12, pad=20)
        
        # Subplot 4: Order Book Dynamics
        ax4 = axes[1, 1]
        # Moving average of orders
        if data['orders'].sum() > 0:
            window = min(50, len(data) // 10)
            if window > 0:
                ma_orders = data['orders'].rolling(window=window, center=True).mean()
                ax4.plot(data['t'], data['orders'], color=COLORS['best_bid'], 
                        alpha=0.3, linewidth=0.5, label='Orders')
                ax4.plot(data['t'], ma_orders, color=COLORS['best_ask'], 
                        linewidth=2, label=f'{window}-Step MA')
                ax4.set_xlabel('Time Step', fontsize=11)
                ax4.set_ylabel('Number of Orders', fontsize=11)
                ax4.set_title('Orderbook Depth Evolution', fontsize=12)
                ax4.legend()
                ax4.grid(True, alpha=0.3)
        else:
            ax4.text(0.5, 0.5, 'No Orders', ha='center', va='center',
                    transform=ax4.transAxes, fontsize=14)
        
        plt.tight_layout()
        output_file = output_dir / 'statistics_summary.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def create_product_plots(self, pid: int):
        """
        Create all plots for a single product.
        
        Args:
            pid: Product ID (0-95)
        """
        product_name = self.get_product_name(pid)
        output_dir = self.output_base / 'by_product' / product_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"  📊 Creating plots for {product_name}...")
        
        # Create activity plot
        self.plot_product_activity(pid, output_dir)
        
        # Create statistics plot
        self.plot_product_statistics(pid, output_dir)
        
        return product_name
    
    def create_hourly_comparison(self, hour: int):
        """
        Create comparison plot for all quarters of a specific hour.
        
        Args:
            hour: Hour (0-23)
        """
        output_dir = self.output_base / 'by_hour' / f'H{hour:02d}'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Hour {hour:02d} - Quarterly Comparison', fontsize=16, fontweight='bold')
        
        for q in range(4):
            pid = hour * 4 + q
            data = self.extract_product_data(pid)
            product_name = self.get_product_name(pid)
            
            row = q // 2
            col = q % 2
            ax = axes[row, col]
            
            # Plot cumulative volume
            ax.plot(data['t'], data['cumulative_volume'], linewidth=2, label='Cumulative Volume')
            ax.fill_between(data['t'], 0, data['cumulative_volume'], alpha=0.3)
            
            # Plot trades as bars on secondary axis
            ax2 = ax.twinx()
            ax2.bar(data['t'], data['trades'], alpha=0.3, color=COLORS['volume'], width=1)
            
            ax.set_xlabel('Time Step', fontsize=10)
            ax.set_ylabel('Cumulative Volume (MW)', fontsize=10, color='tab:blue')
            ax2.set_ylabel('Trades per Step', fontsize=10, color='tab:orange')
            ax.set_title(product_name, fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Add statistics
            total_volume = data['cumulative_volume'].iloc[-1]
            total_trades = data['cumulative_trades'].iloc[-1]
            ax.text(0.02, 0.98, f'Vol: {total_volume:.0f} MW\nTrades: {total_trades:.0f}',
                   transform=ax.transAxes, fontsize=9, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        output_file = output_dir / 'quarterly_comparison.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"  ✅ Created hourly comparison for H{hour:02d}")
        
        return output_file
    
    def create_market_heatmap(self):
        """
        Create heatmap showing trade activity across all products and time.
        """
        output_dir = self.output_base / 'summary'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("  📊 Creating market-wide heatmap...")
        
        # Create matrix: 96 products × timesteps
        n_products = 96
        n_steps = len(self.df)
        
        # Sample every N steps for visualization (otherwise too dense)
        step_sample = max(1, n_steps // 300)  # Max 300 columns
        sampled_steps = range(0, n_steps, step_sample)
        
        heatmap_data = np.zeros((n_products, len(sampled_steps)))
        
        for pid in range(n_products):
            data = self.extract_product_data(pid)
            heatmap_data[pid, :] = data.iloc[sampled_steps]['trades'].values
        
        # Create plot
        fig, ax = plt.subplots(figsize=(20, 12))
        
        im = ax.imshow(heatmap_data, aspect='auto', cmap='YlOrRd', interpolation='nearest')
        
        ax.set_xlabel('Time Step', fontsize=12)
        ax.set_ylabel('Product', fontsize=12)
        ax.set_title('Market-Wide Trade Activity Heatmap', fontsize=16, fontweight='bold')
        
        # Set y-ticks to show product names
        ytick_positions = range(0, n_products, 4)  # Every hour
        ytick_labels = [self.get_product_name(i) for i in ytick_positions]
        ax.set_yticks(ytick_positions)
        ax.set_yticklabels(ytick_labels, fontsize=8)
        
        # Set x-ticks
        xtick_positions = range(0, len(sampled_steps), len(sampled_steps)//10)
        xtick_labels = [str(sampled_steps[i]) for i in xtick_positions]
        ax.set_xticks(xtick_positions)
        ax.set_xticklabels(xtick_labels)
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Trades per Step', rotation=270, labelpad=20, fontsize=12)
        
        plt.tight_layout()
        output_file = output_dir / 'market_heatmap.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✅ Created market heatmap")
        
        return output_file
    
    def create_summary_dashboard(self):
        """
        Create overall summary dashboard.
        """
        output_dir = self.output_base / 'summary'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("  📊 Creating summary dashboard...")
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Calculate aggregate statistics
        total_trades_per_step = self.df['n_trades']
        total_volume_per_step = self.df['total_volume']
        n_open_products = self.df['n_open_products']
        total_orders = self.df['total_orders']
        
        # Plot 1: Total Trades Over Time
        ax1 = fig.add_subplot(gs[0, :2])
        ax1.plot(self.df['t'], total_trades_per_step, color=COLORS['midprice'], linewidth=1.5)
        ax1.fill_between(self.df['t'], 0, total_trades_per_step, alpha=0.3, color=COLORS['midprice'])
        ax1.set_ylabel('Trades per Step', fontsize=12)
        ax1.set_title('Total Market Trading Activity', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Open Products
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.plot(self.df['t'], n_open_products, color=COLORS['best_bid'], linewidth=2)
        ax2.fill_between(self.df['t'], 0, n_open_products, alpha=0.3, color=COLORS['best_bid'])
        ax2.set_ylabel('Number of Products', fontsize=12)
        ax2.set_title('Open Products', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Cumulative Volume
        ax3 = fig.add_subplot(gs[1, :2])
        cumulative_volume = total_volume_per_step.cumsum()
        ax3.plot(self.df['t'], cumulative_volume, color=COLORS['volume'], linewidth=2)
        ax3.fill_between(self.df['t'], 0, cumulative_volume, alpha=0.3, color=COLORS['volume'])
        ax3.set_ylabel('Cumulative Volume (MW)', fontsize=12)
        ax3.set_title('Total Market Volume', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        
        # Add final volume annotation
        final_volume = cumulative_volume.iloc[-1]
        ax3.text(0.98, 0.98, f'Total: {final_volume:,.0f} MW',
                transform=ax3.transAxes, fontsize=12, fontweight='bold',
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
        
        # Plot 4: Total Orders
        ax4 = fig.add_subplot(gs[1, 2])
        ax4.plot(self.df['t'], total_orders, color=COLORS['best_ask'], linewidth=1.5)
        ax4.set_ylabel('Number of Orders', fontsize=12)
        ax4.set_title('Total Orders in Market', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        
        # Plot 5: Trade Distribution per Product
        ax5 = fig.add_subplot(gs[2, :])
        product_totals = []
        for pid in range(96):
            data = self.extract_product_data(pid)
            product_totals.append(data['cumulative_trades'].iloc[-1])
        
        x_pos = range(96)
        colors_by_hour = [plt.cm.viridis(i/24) for i in range(24) for _ in range(4)]
        ax5.bar(x_pos, product_totals, color=colors_by_hour, alpha=0.7)
        ax5.set_xlabel('Product ID', fontsize=12)
        ax5.set_ylabel('Total Trades', fontsize=12)
        ax5.set_title('Trade Distribution Across All Products', fontsize=14, fontweight='bold')
        ax5.grid(True, alpha=0.3, axis='y')
        
        # Add hour markers
        for h in range(0, 96, 4):
            ax5.axvline(h, color='gray', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        output_file = output_dir / 'market_summary.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print("  ✅ Created summary dashboard")
        
        return output_file
    
    def run_all_plots(self, parallel: bool = True, n_processes: int = 4):
        """
        Create all plots for the simulation.
        
        Args:
            parallel: Use parallel processing for product plots
            n_processes: Number of parallel processes
        """
        print("\n" + "="*70)
        print("📊 CREATING ALL PLOTS FOR 96-PRODUCT SIMULATION")
        print("="*70)
        
        # 1. Individual Product Plots
        print("\n1️⃣ Creating individual product plots...")
        if parallel:
            with Pool(n_processes) as pool:
                pool.map(self.create_product_plots, range(96))
        else:
            for pid in range(96):
                self.create_product_plots(pid)
        
        print(f"✅ Created plots for all 96 products")
        
        # 2. Hourly Comparison Plots
        print("\n2️⃣ Creating hourly comparison plots...")
        for hour in range(24):
            self.create_hourly_comparison(hour)
        print(f"✅ Created hourly comparisons for all 24 hours")
        
        # 3. Summary Plots
        print("\n3️⃣ Creating summary plots...")
        self.create_market_heatmap()
        self.create_summary_dashboard()
        print(f"✅ Created summary plots")
        
        print("\n" + "="*70)
        print(f"🎉 ALL PLOTS CREATED!")
        print(f"📁 Output directory: {self.output_base}")
        print("="*70)


def main():
    """Main execution function."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python plot_96_products.py <csv_file>")
        print("Example: python plot_96_products.py results/demo4_quarterly_96products.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"❌ Error: File not found: {csv_file}")
        sys.exit(1)
    
    # Create plotter
    plotter = ProductPlotter(csv_file)
    
    # Run all plots
    plotter.run_all_plots(parallel=True, n_processes=4)


if __name__ == "__main__":
    main()