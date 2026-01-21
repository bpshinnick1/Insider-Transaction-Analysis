"""
Main trading bot that orchestrates data collection, signal generation, and trade execution.
"""

import time
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logger import setup_logger
from src.utils.config import config
from src.utils.database import Database
from src.data_collection.scraper import OpenInsiderScraper
from src.analysis.signal_generator import SignalGenerator
from src.trading.ibkr_client import IBKRClient

logger = setup_logger('trader')


class TradingBot:
    """
    Main trading bot that coordinates all components.
    """
    
    def __init__(self, paper_trading: bool = True):
        """
        Initialize trading bot.
        
        Args:
            paper_trading: If True, use paper trading mode
        """
        self.paper_trading = paper_trading
        self.db = Database()
        self.scraper = OpenInsiderScraper()
        self.signal_generator = SignalGenerator()
        self.ibkr_client = IBKRClient()
        
        self.running = False
    
    def start(self):
        """Start the trading bot."""
        logger.info("="*60)
        logger.info("INSIDER TRADING BOT STARTING")
        logger.info("="*60)
        
        mode = "PAPER TRADING" if self.paper_trading else "LIVE TRADING"
        logger.info(f"Mode: {mode}")
        logger.info(f"Min Transaction Value: ${config.min_transaction_value:,.0f}")
        logger.info(f"Max Positions: {config.max_positions}")
        logger.info(f"Position Size: {config.position_size_pct*100:.1f}% per trade")
        logger.info("="*60)
        
        # Connect to IBKR
        if not self.ibkr_client.connect():
            logger.error("Failed to connect to IBKR. Bot cannot start.")
            return
        
        self.running = True
        
        try:
            # Initial run
            self._run_cycle()
            
            # Main loop
            while self.running:
                logger.info(f"Next cycle in {config.scrape_interval_hours} hours...")
                time.sleep(config.scrape_interval_hours * 3600)
                
                if self.running:
                    self._run_cycle()
        
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.stop()
    
    def _run_cycle(self):
        """Run one complete cycle of the bot."""
        logger.info("\n" + "="*60)
        logger.info(f"CYCLE START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        # Step 1: Scrape new insider transactions
        logger.info("\n[1/4] Scraping insider transactions...")
        try:
            transactions = self.scraper.scrape_recent_transactions()
            significant = self.scraper.filter_significant_purchases(transactions)
            
            # Save to database
            new_count = 0
            for _, row in significant.iterrows():
                if self.db.add_transaction(row.to_dict()):
                    new_count += 1
            
            logger.info(f"Found {new_count} new significant transactions")
        except Exception as e:
            logger.error(f"Error in scraping: {e}")
        
        # Step 2: Generate trading signals
        logger.info("\n[2/4] Generating trading signals...")
        try:
            signals = self.signal_generator.generate_signals()
            logger.info(f"Generated {len(signals)} new signals")
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            signals = []
        
        # Step 3: Execute trades for new signals
        logger.info("\n[3/4] Executing trades...")
        try:
            self._execute_signals(signals)
        except Exception as e:
            logger.error(f"Error executing trades: {e}")
        
        # Step 4: Manage existing positions
        logger.info("\n[4/4] Managing existing positions...")
        try:
            self._manage_positions()
        except Exception as e:
            logger.error(f"Error managing positions: {e}")
        
        # Portfolio summary
        self._print_portfolio_summary()
        
        logger.info("\n" + "="*60)
        logger.info("CYCLE COMPLETE")
        logger.info("="*60 + "\n")
    
    def _execute_signals(self, signals: List[Dict]):
        """Execute trades for new signals."""
        if not signals:
            logger.info("No new signals to execute")
            return
        
        # Check current positions
        current_positions = len(self.db.get_open_trades())
        
        if current_positions >= config.max_positions:
            logger.warning(f"Already at max positions ({config.max_positions})")
            return
        
        # Get account summary
        account = self.ibkr_client.get_account_summary()
        if not account:
            logger.error("Could not get account summary")
            return
        
        available_cash = account.get('TotalCashValue', 0)
        
        # Execute each signal
        executed = 0
        for signal in signals:
            if current_positions + executed >= config.max_positions:
                logger.info(f"Reached max positions limit")
                break
            
            ticker = signal['ticker']
            shares = signal['target_position_size']
            entry_price = signal['entry_price']
            
            # Calculate order value
            order_value = shares * entry_price
            
            if order_value > available_cash:
                logger.warning(f"Insufficient cash for {ticker}: need ${order_value:,.2f}, have ${available_cash:,.2f}")
                continue
            
            # Place limit order with small tolerance
            limit_price = entry_price * 1.01  # 1% above current price
            
            logger.info(f"Placing order: {ticker} {shares} shares @ ${limit_price:.2f}")
            
            order_result = self.ibkr_client.place_limit_order(
                ticker=ticker,
                shares=shares,
                limit_price=limit_price,
                action='BUY'
            )
            
            if order_result:
                # Record trade in database
                trade_data = {
                    'signal_id': signal['signal_id'],
                    'ticker': ticker,
                    'entry_date': datetime.utcnow(),
                    'entry_price': entry_price,
                    'shares': shares,
                    'status': 'OPEN',
                    'ibkr_order_id': str(order_result['order_id']),
                    'notes': f"Signal strength: {signal['signal_strength']}"
                }
                
                self.db.add_trade(trade_data)
                
                available_cash -= order_value
                executed += 1
                
                logger.info(f"✓ Trade executed: {ticker}")
            else:
                logger.error(f"✗ Failed to place order for {ticker}")
        
        logger.info(f"Executed {executed} trades")
    
    def _manage_positions(self):
        """Manage existing open positions."""
        open_trades = self.db.get_open_trades()
        
        if not open_trades:
            logger.info("No open positions to manage")
            return
        
        logger.info(f"Managing {len(open_trades)} open positions")
        
        for trade in open_trades:
            ticker = trade.ticker
            entry_price = trade.entry_price
            entry_date = trade.entry_date
            shares = trade.shares
            
            # Get current price
            current_price = self.ibkr_client.get_market_price(ticker)
            
            if not current_price:
                logger.warning(f"Could not get price for {ticker}")
                continue
            
            # Calculate P&L
            current_value = shares * current_price
            entry_value = shares * entry_price
            pnl = current_value - entry_value
            pnl_pct = pnl / entry_value
            
            # Calculate holding period
            holding_days = (datetime.utcnow() - entry_date).days
            
            logger.debug(f"{ticker}: ${current_price:.2f} ({pnl_pct*100:+.1f}%), {holding_days} days")
            
            # Check exit conditions
            should_exit = False
            exit_reason = None
            
            # Stop loss
            if current_price <= entry_price * (1 - config.stop_loss_pct):
                should_exit = True
                exit_reason = 'STOP_LOSS'
                logger.info(f"{ticker} hit stop loss: ${current_price:.2f}")
            
            # Profit target
            elif current_price >= entry_price * (1 + config.profit_target_pct):
                should_exit = True
                exit_reason = 'PROFIT_TARGET'
                logger.info(f"{ticker} hit profit target: ${current_price:.2f}")
            
            # Time-based exit
            elif holding_days >= config.hold_period_days:
                should_exit = True
                exit_reason = 'TIME_BASED'
                logger.info(f"{ticker} reached holding period: {holding_days} days")
            
            # Execute exit
            if should_exit:
                logger.info(f"Exiting {ticker}: {exit_reason}")
                
                order_result = self.ibkr_client.place_market_order(
                    ticker=ticker,
                    shares=shares,
                    action='SELL'
                )
                
                if order_result:
                    # Update trade in database
                    self.db.update_trade(
                        trade.id,
                        exit_date=datetime.utcnow(),
                        exit_price=current_price,
                        exit_reason=exit_reason,
                        gross_pnl=pnl,
                        net_pnl=pnl,  # Simplified, should account for commissions
                        return_pct=pnl_pct,
                        status='CLOSED'
                    )
                    
                    logger.info(f"✓ Closed {ticker}: ${pnl:+,.2f} ({pnl_pct*100:+.1f}%)")
                else:
                    logger.error(f"✗ Failed to close {ticker}")
    
    def _print_portfolio_summary(self):
        """Print current portfolio status."""
        logger.info("\n" + "-"*60)
        logger.info("PORTFOLIO SUMMARY")
        logger.info("-"*60)
        
        # Account summary
        account = self.ibkr_client.get_account_summary()
        if account:
            logger.info(f"Total Value: ${account.get('NetLiquidation', 0):,.2f}")
            logger.info(f"Cash: ${account.get('TotalCashValue', 0):,.2f}")
            logger.info(f"Buying Power: ${account.get('BuyingPower', 0):,.2f}")
        
        # Open positions
        open_trades = self.db.get_open_trades()
        logger.info(f"\nOpen Positions: {len(open_trades)}")
        
        if open_trades:
            for trade in open_trades:
                current_price = self.ibkr_client.get_market_price(trade.ticker)
                if current_price:
                    pnl_pct = (current_price - trade.entry_price) / trade.entry_price
                    logger.info(f"  {trade.ticker}: {trade.shares} shares @ ${trade.entry_price:.2f} "
                              f"(now ${current_price:.2f}, {pnl_pct*100:+.1f}%)")
        
        # Recent closed trades
        all_trades = self.db.get_all_trades()
        closed_trades = [t for t in all_trades if t.status == 'CLOSED']
        
        if closed_trades:
            logger.info(f"\nClosed Trades (last 5):")
            for trade in closed_trades[-5:]:
                logger.info(f"  {trade.ticker}: {trade.exit_reason}, "
                          f"${trade.net_pnl:+,.2f} ({trade.return_pct*100:+.1f}%)")
        
        logger.info("-"*60 + "\n")
    
    def stop(self):
        """Stop the trading bot."""
        logger.info("Shutting down trading bot...")
        
        self.running = False
        
        # Disconnect from IBKR
        self.ibkr_client.disconnect()
        
        # Close database
        self.db.close()
        self.signal_generator.close()
        
        logger.info("Trading bot stopped")


def main():
    """Run the trading bot."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run the insider trading bot')
    parser.add_argument('--mode', choices=['paper', 'live'], default='paper',
                       help='Trading mode (default: paper)')
    
    args = parser.parse_args()
    
    paper_trading = (args.mode == 'paper')
    
    # Safety check
    if not paper_trading:
        confirm = input("\n⚠️  WARNING: You are about to start LIVE TRADING with real money!\n"
                       "Type 'CONFIRM' to proceed: ")
        if confirm != 'CONFIRM':
            print("Live trading cancelled")
            return
    
    # Start bot
    bot = TradingBot(paper_trading=paper_trading)
    bot.start()


if __name__ == "__main__":
    main()
