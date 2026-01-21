"""
Configuration loader for the trading bot.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any


class Config:
    """Configuration manager for trading bot."""
    
    def __init__(self, env_file: str = None):
        """Load configuration from .env file."""
        if env_file is None:
            env_file = Path(__file__).parent.parent.parent / 'config' / '.env'
        
        if Path(env_file).exists():
            load_dotenv(env_file)
    
    # Interactive Brokers Settings
    @property
    def ibkr_host(self) -> str:
        return os.getenv('IBKR_HOST', '127.0.0.1')
    
    @property
    def ibkr_port(self) -> int:
        return int(os.getenv('IBKR_PORT', '7497'))
    
    @property
    def ibkr_client_id(self) -> int:
        return int(os.getenv('IBKR_CLIENT_ID', '1'))
    
    @property
    def paper_trading(self) -> bool:
        return os.getenv('PAPER_TRADING', 'True').lower() == 'true'
    
    # Trading Parameters
    @property
    def min_transaction_value(self) -> float:
        return float(os.getenv('MIN_TRANSACTION_VALUE', '100000'))
    
    @property
    def position_size_pct(self) -> float:
        return float(os.getenv('POSITION_SIZE_PCT', '0.02'))
    
    @property
    def max_positions(self) -> int:
        return int(os.getenv('MAX_POSITIONS', '10'))
    
    @property
    def stop_loss_pct(self) -> float:
        return float(os.getenv('STOP_LOSS_PCT', '0.03'))
    
    @property
    def profit_target_pct(self) -> float:
        return float(os.getenv('PROFIT_TARGET_PCT', '0.06'))
    
    @property
    def hold_period_days(self) -> int:
        return int(os.getenv('HOLD_PERIOD_DAYS', '10'))
    
    # Data Collection
    @property
    def scrape_interval_hours(self) -> int:
        return int(os.getenv('SCRAPE_INTERVAL_HOURS', '4'))
    
    @property
    def lookback_days(self) -> int:
        return int(os.getenv('LOOKBACK_DAYS', '7'))
    
    @property
    def sec_user_agent(self) -> str:
        return os.getenv('SEC_USER_AGENT', 'TradingBot admin@example.com')
    
    # Risk Management
    @property
    def max_daily_trades(self) -> int:
        return int(os.getenv('MAX_DAILY_TRADES', '5'))
    
    @property
    def max_portfolio_exposure(self) -> float:
        return float(os.getenv('MAX_PORTFOLIO_EXPOSURE', '0.20'))
    
    @property
    def min_stock_price(self) -> float:
        return float(os.getenv('MIN_STOCK_PRICE', '5.00'))
    
    @property
    def max_stock_price(self) -> float:
        return float(os.getenv('MAX_STOCK_PRICE', '1000.00'))
    
    @property
    def min_market_cap(self) -> float:
        return float(os.getenv('MIN_MARKET_CAP', '1000000000'))
    
    # Database
    @property
    def database_path(self) -> str:
        return os.getenv('DATABASE_PATH', 'data/trading_bot.db')
    
    # Logging
    @property
    def log_level(self) -> str:
        return os.getenv('LOG_LEVEL', 'INFO')
    
    @property
    def log_file(self) -> str:
        return os.getenv('LOG_FILE', 'logs/trading_bot.log')
    
    # Backtesting
    @property
    def backtest_start_date(self) -> str:
        return os.getenv('BACKTEST_START_DATE', '2020-01-01')
    
    @property
    def backtest_end_date(self) -> str:
        return os.getenv('BACKTEST_END_DATE', '2024-12-31')
    
    @property
    def backtest_initial_capital(self) -> float:
        return float(os.getenv('BACKTEST_INITIAL_CAPITAL', '100000'))
    
    @property
    def backtest_commission(self) -> float:
        return float(os.getenv('BACKTEST_COMMISSION', '0.001'))
    
    @property
    def backtest_slippage(self) -> float:
        return float(os.getenv('BACKTEST_SLIPPAGE', '0.001'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'ibkr': {
                'host': self.ibkr_host,
                'port': self.ibkr_port,
                'client_id': self.ibkr_client_id,
                'paper_trading': self.paper_trading,
            },
            'trading': {
                'min_transaction_value': self.min_transaction_value,
                'position_size_pct': self.position_size_pct,
                'max_positions': self.max_positions,
                'stop_loss_pct': self.stop_loss_pct,
                'profit_target_pct': self.profit_target_pct,
                'hold_period_days': self.hold_period_days,
            },
            'risk': {
                'max_daily_trades': self.max_daily_trades,
                'max_portfolio_exposure': self.max_portfolio_exposure,
                'min_stock_price': self.min_stock_price,
                'max_stock_price': self.max_stock_price,
                'min_market_cap': self.min_market_cap,
            },
            'data_collection': {
                'scrape_interval_hours': self.scrape_interval_hours,
                'lookback_days': self.lookback_days,
            }
        }


# Create global config instance
config = Config()


if __name__ == "__main__":
    # Display configuration
    conf = Config()
    print("Trading Bot Configuration")
    print("=" * 50)
    
    import json
    print(json.dumps(conf.to_dict(), indent=2))
