"""
Structured Logging for Intraday Market Simulation

Provides clean, professional logging with:
- Different log levels (DEBUG, INFO, WARNING, ERROR)
- Console and file output
- Colored console output (optional)
- Timestamps
- Module/function tracking

Usage:
    from intraday_abm.utils.logging import setup_logger, get_logger
    
    # Setup once at start
    logger = setup_logger('demo4', log_file='results/logs/demo4.log')
    
    # Use throughout code
    logger.info("Simulation started")
    logger.debug("Agent 5 placed order: %s", order)
    logger.warning("Low liquidity detected")
    logger.error("Critical error occurred")
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# ANSI color codes for terminal output
class LogColors:
    """ANSI color codes for colored console output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Level colors
    DEBUG = CYAN
    INFO = GREEN
    WARNING = YELLOW
    ERROR = RED
    CRITICAL = RED + BOLD


class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to console output"""
    
    FORMATS = {
        logging.DEBUG: LogColors.DEBUG + '%(levelname)-8s' + LogColors.RESET + ' | %(message)s',
        logging.INFO: LogColors.INFO + '%(levelname)-8s' + LogColors.RESET + ' | %(message)s',
        logging.WARNING: LogColors.WARNING + '%(levelname)-8s' + LogColors.RESET + ' | %(message)s',
        logging.ERROR: LogColors.ERROR + '%(levelname)-8s' + LogColors.RESET + ' | %(message)s',
        logging.CRITICAL: LogColors.CRITICAL + '%(levelname)-8s' + LogColors.RESET + ' | %(message)s',
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(
            f'%(asctime)s | {log_fmt}',
            datefmt='%H:%M:%S'
        )
        return formatter.format(record)


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = 'INFO',
    log_to_console: bool = True,
    use_colors: bool = True,
) -> logging.Logger:
    """
    Setup structured logger for simulation.
    
    Args:
        name: Logger name (e.g., 'demo4', 'simulation')
        log_file: Path to log file (optional)
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        log_to_console: Whether to print to console
        use_colors: Whether to use colored output (console only)
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = setup_logger('demo4', log_file='results/logs/demo4.log')
        >>> logger.info("Simulation started with %d agents", n_agents)
        >>> logger.warning("Low liquidity detected for product %d", product_id)
    """
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # Console Handler
    if log_to_console:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(getattr(logging, level.upper()))
        
        if use_colors and sys.stdout.isatty():
            # Use colored formatter for terminal
            console.setFormatter(ColoredFormatter())
        else:
            # Use plain formatter for file redirection
            console_fmt = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console.setFormatter(console_fmt)
        
        logger.addHandler(console)
    
    # File Handler
    if log_file:
        # Create directory if needed
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        
        file_fmt = logging.Formatter(
            '%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_fmt)
        
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get existing logger by name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
        
    Example:
        >>> logger = get_logger('demo4')
        >>> logger.info("Using existing logger")
    """
    return logging.getLogger(name)


class SimulationLogger:
    """
    High-level logger for simulation with convenience methods.
    
    Provides specialized logging for common simulation events.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def simulation_start(self, n_steps: int, n_agents: int, n_products: int):
        """Log simulation start"""
        self.logger.info("="*70)
        self.logger.info("SIMULATION STARTED")
        self.logger.info("="*70)
        self.logger.info("Steps: %d, Agents: %d, Products: %d", n_steps, n_agents, n_products)
    
    def simulation_end(self, total_trades: int, total_volume: float, elapsed_time: float):
        """Log simulation end"""
        self.logger.info("="*70)
        self.logger.info("SIMULATION COMPLETED")
        self.logger.info("="*70)
        self.logger.info("Total Trades: %d, Total Volume: %.1f MW, Time: %.2f s", 
                        total_trades, total_volume, elapsed_time)
    
    def progress(self, step: int, n_steps: int, open_products: int, trades: int, volume: float):
        """Log progress update"""
        if step % 50 == 0:  # Every 50 steps
            progress_pct = (step / n_steps) * 100
            self.logger.info("Progress: %5.1f%% | Step %4d/%d | Open: %2d | Trades: %3d | Volume: %8.1f MW",
                           progress_pct, step, n_steps, open_products, trades, volume)
    
    def agent_created(self, agent_type: str, agent_id: int, **params):
        """Log agent creation"""
        param_str = ", ".join(f"{k}={v}" for k, v in params.items())
        self.logger.debug("Agent created: %s (ID=%d) - %s", agent_type, agent_id, param_str)
    
    def order_placed(self, agent_id: int, product_id: int, side: str, price: float, volume: float):
        """Log order placement"""
        self.logger.debug("Order placed: Agent %d, Product %d, %s %.2f €/MWh, %.2f MW",
                         agent_id, product_id, side, price, volume)
    
    def trade_executed(self, product_id: int, price: float, volume: float):
        """Log trade execution"""
        self.logger.debug("Trade executed: Product %d, %.2f €/MWh, %.2f MW",
                         product_id, price, volume)
    
    def product_closed(self, product_id: int, product_name: str, total_trades: int, total_volume: float):
        """Log product closure"""
        self.logger.info("Product closed: %s (ID=%d) - Trades: %d, Volume: %.1f MW",
                        product_name, product_id, total_trades, total_volume)
    
    def warning_low_liquidity(self, product_id: int, n_orders: int):
        """Log low liquidity warning"""
        self.logger.warning("Low liquidity: Product %d has only %d orders", product_id, n_orders)
    
    def warning_no_trades(self, step: int, consecutive_steps: int):
        """Log no trading activity warning"""
        self.logger.warning("No trades for %d consecutive steps (current: %d)", consecutive_steps, step)
    
    def error_order_invalid(self, agent_id: int, reason: str):
        """Log invalid order error"""
        self.logger.error("Invalid order from Agent %d: %s", agent_id, reason)
    
    def market_statistics(self, step: int, stats: dict):
        """Log market statistics"""
        self.logger.info("Market Stats (Step %d): Spread=%.2f, Midprice=%.2f, Volume=%.1f",
                        step, stats.get('spread', 0), stats.get('midprice', 0), stats.get('volume', 0))


# Convenience function for quick setup
def quick_logger(name: str = 'simulation', level: str = 'INFO') -> SimulationLogger:
    """
    Quick setup for simulation logger with sensible defaults.
    
    Args:
        name: Logger name
        level: Log level
        
    Returns:
        SimulationLogger instance
        
    Example:
        >>> logger = quick_logger('demo4')
        >>> logger.simulation_start(1500, 25, 96)
    """
    base_logger = setup_logger(
        name=name,
        log_file=f'results/logs/{name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
        level=level,
        log_to_console=True,
        use_colors=True
    )
    return SimulationLogger(base_logger)


if __name__ == "__main__":
    # Demo of logging functionality
    print("=== Logging Demo ===\n")
    
    # Setup logger
    logger = setup_logger(
        'demo',
        log_file='test_logging.log',
        level='DEBUG'
    )
    
    # Test different log levels
    logger.debug("This is a DEBUG message (detailed)")
    logger.info("This is an INFO message (normal)")
    logger.warning("This is a WARNING message (attention needed)")
    logger.error("This is an ERROR message (something went wrong)")
    
    print("\n=== SimulationLogger Demo ===\n")
    
    # Use high-level logger
    sim_logger = SimulationLogger(logger)
    sim_logger.simulation_start(1500, 25, 96)
    sim_logger.progress(50, 1500, 10, 150, 1250.5)
    sim_logger.agent_created('Variable', 0, capacity=150.0, limit_buy=55.0)
    sim_logger.product_closed(0, 'H00Q1', 523, 3250.0)
    sim_logger.simulation_end(52000, 365000, 45.2)
    
    print("\n=== Quick Logger Demo ===\n")
    
    quick = quick_logger('quick_demo')
    quick.simulation_start(100, 10, 24)
    quick.warning_low_liquidity(5, 3)
    
    print(f"\nLog file created: test_logging.log")