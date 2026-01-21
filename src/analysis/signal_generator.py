"""
Trading signal generator.
Analyzes insider transactions and generates buy signals based on rules.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import uuid
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logger import setup_logger
from src.utils.config import config
from src.utils.database import Database
from src.data_collection.price_fetcher import PriceFetcher

logger = setup_logger('signal_generator')


class SignalGenerator:
    """Generate trading signals from insider transaction data."""
    
    def __init__(self):
        """Initialize signal generator."""
        self.db = Database()
        self.price_fetcher = PriceFetcher()
    
    def generate_signals(self) -> List[Dict]:
        """
        Generate new trading signals from recent insider transactions.
        
        Returns:
            List of signal dictionaries
        """
        logger.info("Generating trading signals...")
        
        # Get recent transactions from database
        transactions = self.db.get_recent_transactions(days=config.lookback_days)
        
        if not transactions:
            logger.info("No recent transactions found")
            return []
        
        logger.info(f"Analyzing {len(transactions)} transactions")
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([{
            'id': t.id,
            'ticker': t.ticker,
            'insider_name': t.insider_name,
            'insider_title': t.insider_title,
            'transaction_date': t.transaction_date,
            'filing_date': t.filing_date,
            'total_value': t.total_value,
            'shares': t.shares,
            'price_per_share': t.price_per_share,
        } for t in transactions])
        
        # Generate signals
        signals = []
        
        for ticker in df['ticker'].unique():
            ticker_df = df[df['ticker'] == ticker]
            signal = self._analyze_ticker(ticker, ticker_df)
            
            if signal:
                signals.append(signal)
        
        # Save signals to database
        saved_count = 0
        for signal in signals:
            try:
                self.db.add_signal(signal)
                saved_count += 1
                logger.info(f"Signal generated: {signal['ticker']} ({signal['signal_strength']}) - "
                           f"Entry: ${signal['entry_price']:.2f}")
            except Exception as e:
                logger.error(f"Error saving signal: {e}")
        
        logger.info(f"Generated {saved_count} new signals")
        return signals
    
    def _analyze_ticker(self, ticker: str, transactions: pd.DataFrame) -> Optional[Dict]:
        """
        Analyze transactions for a specific ticker and generate signal if appropriate.
        
        Args:
            ticker: Stock ticker
            transactions: DataFrame of transactions for this ticker
        
        Returns:
            Signal dictionary or None
        """
        try:
            # Get current price
            current_price = self.price_fetcher.get_current_price(ticker)
            
            if not current_price:
                logger.warning(f"Could not get price for {ticker}")
                return None
            
            # Check if price is within acceptable range
            if current_price < config.min_stock_price or current_price > config.max_stock_price:
                logger.debug(f"{ticker} price ${current_price:.2f} outside acceptable range")
                return None
            
            # Calculate conviction score
            conviction_score = self._calculate_conviction(transactions)
            
            # Determine signal strength
            signal_strength = self._determine_signal_strength(conviction_score)
            
            if signal_strength == 'NONE':
                return None
            
            # Calculate position sizing
            position_size = self._calculate_position_size(current_price, conviction_score)
            
            # Calculate stop loss and profit target
            stop_loss = current_price * (1 - config.stop_loss_pct)
            profit_target = current_price * (1 + config.profit_target_pct)
            
            # Get the most recent transaction ID for reference
            transaction_id = transactions.iloc[0]['id']
            
            # Create signal
            signal = {
                'signal_id': str(uuid.uuid4()),
                'ticker': ticker,
                'transaction_id': transaction_id,
                'signal_date': datetime.utcnow(),
                'signal_strength': signal_strength,
                'conviction_score': conviction_score,
                'entry_price': current_price,
                'target_position_size': position_size,
                'stop_loss': stop_loss,
                'profit_target': profit_target,
                'status': 'ACTIVE',
                'notes': self._generate_signal_notes(transactions)
            }
            
            return signal
            
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            return None
    
    def _calculate_conviction(self, transactions: pd.DataFrame) -> float:
        """
        Calculate conviction score (0-100) based on transaction characteristics.
        
        Factors:
        - Transaction size relative to threshold
        - Number of insiders buying
        - Seniority of insiders (CEO/CFO higher weight)
        - Recency of transactions
        - Clustering (multiple buys in short period)
        """
        score = 0.0
        
        # Base score from transaction value
        total_value = transactions['total_value'].sum()
        value_multiplier = total_value / config.min_transaction_value
        score += min(40, 20 * np.log1p(value_multiplier))  # Max 40 points
        
        # Number of distinct insiders buying
        num_insiders = transactions['insider_name'].nunique()
        score += min(20, num_insiders * 5)  # Max 20 points (4+ insiders)
        
        # Insider seniority
        senior_titles = ['CEO', 'Chief Executive', 'CFO', 'Chief Financial']
        has_senior = transactions['insider_title'].str.contains('|'.join(senior_titles), case=False, na=False).any()
        if has_senior:
            score += 20  # 20 points for senior executive
        else:
            score += 10  # 10 points for director
        
        # Recency bonus (transactions within last 3 days)
        recent_cutoff = datetime.now() - timedelta(days=3)
        recent_transactions = transactions[transactions['filing_date'] >= recent_cutoff]
        if len(recent_transactions) > 0:
            score += 10
        
        # Clustering bonus (multiple transactions within 30 days)
        if len(transactions) >= 3:
            score += 10
        
        return min(100, score)
    
    def _determine_signal_strength(self, conviction_score: float) -> str:
        """Determine signal strength based on conviction score."""
        if conviction_score >= 75:
            return 'HIGH'
        elif conviction_score >= 50:
            return 'MEDIUM'
        elif conviction_score >= 30:
            return 'LOW'
        else:
            return 'NONE'
    
    def _calculate_position_size(self, price: float, conviction_score: float) -> int:
        """
        Calculate number of shares to buy.
        
        Uses conviction score to scale position size within limits.
        """
        # Assume a base portfolio value for calculation
        # In production, this would come from the trading account
        base_capital = 100000  # $100k portfolio assumption
        
        # Base position size from config
        base_position_value = base_capital * config.position_size_pct
        
        # Scale by conviction (0.5x to 1.5x based on score)
        conviction_multiplier = 0.5 + (conviction_score / 100)
        
        position_value = base_position_value * conviction_multiplier
        
        # Calculate shares
        shares = int(position_value / price)
        
        # Minimum 10 shares, maximum based on position limits
        shares = max(10, min(shares, 1000))
        
        return shares
    
    def _generate_signal_notes(self, transactions: pd.DataFrame) -> str:
        """Generate descriptive notes for the signal."""
        num_transactions = len(transactions)
        total_value = transactions['total_value'].sum()
        insiders = transactions['insider_name'].unique()
        
        notes = f"{num_transactions} insider purchase(s) totaling ${total_value:,.0f}. "
        notes += f"Insiders: {', '.join(insiders[:3])}"
        
        if len(insiders) > 3:
            notes += f" and {len(insiders) - 3} others"
        
        return notes
    
    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Run signal generation."""
    logger.info("Starting signal generation...")
    
    generator = SignalGenerator()
    
    try:
        signals = generator.generate_signals()
        
        if signals:
            print(f"\n=== Generated {len(signals)} New Signals ===\n")
            
            for signal in signals:
                print(f"Ticker: {signal['ticker']}")
                print(f"  Strength: {signal['signal_strength']}")
                print(f"  Conviction: {signal['conviction_score']:.1f}/100")
                print(f"  Entry Price: ${signal['entry_price']:.2f}")
                print(f"  Position Size: {signal['target_position_size']} shares")
                print(f"  Stop Loss: ${signal['stop_loss']:.2f}")
                print(f"  Profit Target: ${signal['profit_target']:.2f}")
                print(f"  Notes: {signal['notes']}")
                print()
        else:
            print("\nNo new signals generated")
    
    finally:
        generator.close()


if __name__ == "__main__":
    main()
