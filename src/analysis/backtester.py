"""
Backtesting engine for the insider trading bot.
Tests trading strategy on historical data with realistic slippage and fees.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import sys
from pathlib import Path
import argparse

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logger import setup_logger
from src.utils.config import config
from src.data_collection.price_fetcher import PriceFetcher

logger = setup_logger('backtester')


class Backtester:
    """
    Backtesting engine for insider trading strategy.
    """
    
    def __init__(self, initial_capital: float = None, commission: float = None, slippage: float = None):
        """
        Initialize backtester.
        
        Args:
            initial_capital: Starting capital
            commission: Commission per trade (as decimal)
            slippage: Slippage per trade (as decimal)
        """
        self.initial_capital = initial_capital or config.backtest_initial_capital
        self.commission = commission or config.backtest_commission
        self.slippage = slippage or config.backtest_slippage
        
        self.price_fetcher = PriceFetcher()
        
        # Track state
        self.cash = self.initial_capital
        self.positions = {}  # ticker -> {shares, entry_price, entry_date}
        self.trades = []
        self.portfolio_values = []
    
    def load_historical_signals(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load historical insider transactions and generate signals.
        
        For backtesting, we simulate what signals would have been generated.
        """
        logger.info(f"Loading historical data from {start_date} to {end_date}")
        
        # This is a simplified version - in production you'd load real historical filings
        # For now, we'll create a sample dataset
        
        # Sample tickers that historically had insider buying
        sample_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 
                         'AMD', 'NFLX', 'DIS', 'BA', 'JPM', 'V', 'WMT', 'PG']
        
        signals = []
        
        # Generate simulated signals (spread across the date range)
        date_range = pd.date_range(start=start_date, end=end_date, freq='7D')
        
        for signal_date in date_range:
            # Randomly select 1-3 tickers per week
            num_signals = np.random.randint(1, 4)
            selected_tickers = np.random.choice(sample_tickers, num_signals, replace=False)
            
            for ticker in selected_tickers:
                # Get price at signal date
                price_df = self.price_fetcher.get_historical_prices(
                    ticker,
                    (signal_date - timedelta(days=1)).strftime('%Y-%m-%d'),
                    (signal_date + timedelta(days=1)).strftime('%Y-%m-%d')
                )
                
                if not price_df.empty:
                    entry_price = price_df.iloc[0]['close']
                    
                    signals.append({
                        'ticker': ticker,
                        'signal_date': signal_date,
                        'entry_price': entry_price,
                        'conviction_score': np.random.uniform(50, 95),
                    })
        
        df = pd.DataFrame(signals)
        logger.info(f"Generated {len(df)} historical signals")
        
        return df
    
    def run_backtest(self, start_date: str, end_date: str) -> Dict:
        """
        Run backtest over specified date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running backtest from {start_date} to {end_date}")
        
        # Load signals
        signals = self.load_historical_signals(start_date, end_date)
        
        if signals.empty:
            logger.warning("No signals to backtest")
            return {}
        
        # Get SPY data for benchmark
        spy_data = self.price_fetcher.get_historical_prices('SPY', start_date, end_date)
        spy_start = spy_data.iloc[0]['close'] if not spy_data.empty else 100
        spy_end = spy_data.iloc[-1]['close'] if not spy_data.empty else 100
        
        # Process each signal
        for _, signal in signals.iterrows():
            self._process_signal(signal, end_date)
        
        # Close all remaining positions at end date
        self._close_all_positions(end_date)
        
        # Calculate results
        results = self._calculate_results(spy_start, spy_end, start_date, end_date)
        
        return results
    
    def _process_signal(self, signal: pd.Series, backtest_end_date: str):
        """Process a single trading signal."""
        ticker = signal['ticker']
        signal_date = signal['signal_date']
        entry_price = signal['entry_price']
        
        # Calculate position size (simplified)
        position_value = self.cash * config.position_size_pct
        shares = int(position_value / entry_price)
        
        if shares < 10 or self.cash < position_value:
            return  # Not enough cash or position too small
        
        # Check max positions
        if len(self.positions) >= config.max_positions:
            return
        
        # Apply slippage to entry
        actual_entry = entry_price * (1 + self.slippage)
        
        # Calculate costs
        trade_value = shares * actual_entry
        trade_commission = trade_value * self.commission
        total_cost = trade_value + trade_commission
        
        if total_cost > self.cash:
            return
        
        # Enter position
        self.cash -= total_cost
        self.positions[ticker] = {
            'shares': shares,
            'entry_price': actual_entry,
            'entry_date': signal_date,
            'commission_paid': trade_commission
        }
        
        logger.debug(f"Entered {ticker}: {shares} shares @ ${actual_entry:.2f}")
        
        # Calculate exit date/conditions
        exit_date = signal_date + timedelta(days=config.hold_period_days)
        if exit_date > pd.to_datetime(backtest_end_date):
            exit_date = pd.to_datetime(backtest_end_date)
        
        # Get price data for holding period
        price_data = self.price_fetcher.get_historical_prices(
            ticker,
            signal_date.strftime('%Y-%m-%d'),
            exit_date.strftime('%Y-%m-%d')
        )
        
        if price_data.empty:
            # Force exit at entry if no data
            self._exit_position(ticker, actual_entry, exit_date, 'NO_DATA')
            return
        
        # Check for stop loss or profit target during holding period
        stop_loss = actual_entry * (1 - config.stop_loss_pct)
        profit_target = actual_entry * (1 + config.profit_target_pct)
        
        exit_triggered = False
        for _, row in price_data.iterrows():
            if row['low'] <= stop_loss:
                # Stop loss hit
                self._exit_position(ticker, stop_loss, row['date'], 'STOP_LOSS')
                exit_triggered = True
                break
            elif row['high'] >= profit_target:
                # Profit target hit
                self._exit_position(ticker, profit_target, row['date'], 'PROFIT_TARGET')
                exit_triggered = True
                break
        
        # Time-based exit if no other exit triggered
        if not exit_triggered and ticker in self.positions:
            final_price = price_data.iloc[-1]['close']
            self._exit_position(ticker, final_price, exit_date, 'TIME_BASED')
    
    def _exit_position(self, ticker: str, exit_price: float, exit_date, reason: str):
        """Exit a position."""
        if ticker not in self.positions:
            return
        
        position = self.positions[ticker]
        shares = position['shares']
        entry_price = position['entry_price']
        
        # Apply slippage to exit
        actual_exit = exit_price * (1 - self.slippage)
        
        # Calculate proceeds
        proceeds = shares * actual_exit
        exit_commission = proceeds * self.commission
        net_proceeds = proceeds - exit_commission
        
        # Calculate P&L
        gross_pnl = proceeds - (shares * entry_price)
        net_pnl = net_proceeds - (shares * entry_price) - position['commission_paid']
        return_pct = net_pnl / (shares * entry_price)
        
        # Update cash
        self.cash += net_proceeds
        
        # Record trade
        trade = {
            'ticker': ticker,
            'entry_date': position['entry_date'],
            'entry_price': entry_price,
            'exit_date': exit_date,
            'exit_price': actual_exit,
            'shares': shares,
            'exit_reason': reason,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'return_pct': return_pct,
            'holding_days': (exit_date - position['entry_date']).days
        }
        
        self.trades.append(trade)
        
        # Remove position
        del self.positions[ticker]
        
        logger.debug(f"Exited {ticker}: {reason}, P&L: ${net_pnl:.2f} ({return_pct*100:.1f}%)")
    
    def _close_all_positions(self, end_date: str):
        """Close all remaining positions at end of backtest."""
        end_dt = pd.to_datetime(end_date)
        
        for ticker in list(self.positions.keys()):
            # Get final price
            price_data = self.price_fetcher.get_historical_prices(
                ticker,
                (end_dt - timedelta(days=5)).strftime('%Y-%m-%d'),
                end_date
            )
            
            if not price_data.empty:
                final_price = price_data.iloc[-1]['close']
                self._exit_position(ticker, final_price, end_dt, 'BACKTEST_END')
    
    def _calculate_results(self, spy_start: float, spy_end: float, 
                          start_date: str, end_date: str) -> Dict:
        """Calculate backtest performance metrics."""
        if not self.trades:
            return {'error': 'No trades executed'}
        
        trades_df = pd.DataFrame(self.trades)
        
        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['net_pnl'] > 0])
        losing_trades = len(trades_df[trades_df['net_pnl'] <= 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = trades_df['net_pnl'].sum()
        avg_win = trades_df[trades_df['net_pnl'] > 0]['net_pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['net_pnl'] <= 0]['net_pnl'].mean() if losing_trades > 0 else 0
        avg_return = trades_df['return_pct'].mean()
        
        # Final value
        final_value = self.cash
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # Benchmark (SPY)
        spy_return = (spy_end - spy_start) / spy_start
        alpha = total_return - spy_return
        
        # Risk metrics
        returns_series = trades_df['return_pct']
        sharpe_ratio = returns_series.mean() / returns_series.std() * np.sqrt(252) if len(returns_series) > 1 else 0
        
        # Maximum drawdown
        cumulative_returns = (1 + trades_df['return_pct']).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        results = {
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'spy_return': spy_return,
            'alpha': alpha,
            'trades': trades_df
        }
        
        return results
    
    def print_results(self, results: Dict):
        """Print formatted backtest results."""
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"\nPeriod: {results['start_date']} to {results['end_date']}")
        print(f"Initial Capital: ${results['initial_capital']:,.2f}")
        print(f"Final Value: ${results['final_value']:,.2f}")
        print(f"Total P&L: ${results['total_pnl']:,.2f}")
        print(f"Total Return: {results['total_return']*100:.2f}%")
        
        print(f"\n--- Trading Statistics ---")
        print(f"Total Trades: {results['total_trades']}")
        print(f"Winning Trades: {results['winning_trades']} ({results['win_rate']*100:.1f}%)")
        print(f"Losing Trades: {results['losing_trades']}")
        print(f"Average Return: {results['avg_return']*100:.2f}%")
        print(f"Average Win: ${results['avg_win']:,.2f}")
        print(f"Average Loss: ${results['avg_loss']:,.2f}")
        
        print(f"\n--- Risk Metrics ---")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']*100:.2f}%")
        
        print(f"\n--- Benchmark Comparison ---")
        print(f"S&P 500 (SPY) Return: {results['spy_return']*100:.2f}%")
        print(f"Alpha: {results['alpha']*100:.2f}%")
        
        print("\n" + "="*60)


def main():
    """Run backtesting from command line."""
    parser = argparse.ArgumentParser(description='Backtest insider trading strategy')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)', 
                       default=config.backtest_start_date)
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)', 
                       default=config.backtest_end_date)
    parser.add_argument('--capital', type=float, help='Initial capital', 
                       default=config.backtest_initial_capital)
    
    args = parser.parse_args()
    
    # Run backtest
    backtester = Backtester(initial_capital=args.capital)
    results = backtester.run_backtest(args.start_date, args.end_date)
    
    if results:
        backtester.print_results(results)
        
        # Save detailed trades to CSV
        output_dir = Path('data/processed')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f'backtest_results_{timestamp}.csv'
        
        results['trades'].to_csv(output_file, index=False)
        logger.info(f"Detailed results saved to {output_file}")


if __name__ == "__main__":
    main()
