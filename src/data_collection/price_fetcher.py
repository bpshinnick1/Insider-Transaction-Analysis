"""
Price data fetcher using yfinance.
Fetches current and historical stock prices for analysis.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logger import setup_logger

logger = setup_logger('price_fetcher')


class PriceFetcher:
    """Fetch stock price data using yfinance."""
    
    def __init__(self):
        """Initialize price fetcher."""
        pass
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current price for a ticker.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Current price or None if not available
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Try different price fields
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            
            if price:
                logger.debug(f"{ticker}: ${price:.2f}")
                return float(price)
            else:
                logger.warning(f"No price data for {ticker}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e}")
            return None
    
    def get_historical_prices(self, ticker: str, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        Get historical price data.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), default is today
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Fetching {ticker} prices from {start_date} to {end_date}")
            
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date)
            
            if df.empty:
                logger.warning(f"No historical data for {ticker}")
                return pd.DataFrame()
            
            # Clean column names
            df.columns = [col.lower() for col in df.columns]
            df.index.name = 'date'
            df = df.reset_index()
            
            logger.debug(f"Fetched {len(df)} days of data for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {e}")
            return pd.DataFrame()
    
    def get_stock_info(self, ticker: str) -> Dict:
        """
        Get detailed stock information.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with stock information
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Extract relevant fields
            stock_info = {
                'ticker': ticker,
                'company_name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'avg_volume': info.get('averageVolume', 0),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'pe_ratio': info.get('trailingPE'),
            }
            
            return stock_info
            
        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {e}")
            return {'ticker': ticker}
    
    def get_batch_prices(self, tickers: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple tickers.
        
        Args:
            tickers: List of ticker symbols
        
        Returns:
            Dictionary mapping ticker to price
        """
        prices = {}
        
        for ticker in tickers:
            price = self.get_current_price(ticker)
            if price:
                prices[ticker] = price
        
        return prices
    
    def calculate_returns(self, ticker: str, start_date: str, end_date: str = None) -> Optional[float]:
        """
        Calculate total return over a period.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), default is today
        
        Returns:
            Total return as decimal (e.g., 0.15 for 15% gain)
        """
        try:
            df = self.get_historical_prices(ticker, start_date, end_date)
            
            if df.empty or len(df) < 2:
                return None
            
            start_price = df.iloc[0]['close']
            end_price = df.iloc[-1]['close']
            
            total_return = (end_price - start_price) / start_price
            
            return total_return
            
        except Exception as e:
            logger.error(f"Error calculating returns for {ticker}: {e}")
            return None
    
    def is_valid_ticker(self, ticker: str) -> bool:
        """
        Check if a ticker is valid and tradeable.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            True if valid, False otherwise
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Check if we can get basic info
            if not info or 'currentPrice' not in info and 'regularMarketPrice' not in info:
                return False
            
            return True
            
        except Exception:
            return False


def main():
    """Test the price fetcher."""
    fetcher = PriceFetcher()
    
    # Test with a few tickers
    test_tickers = ['AAPL', 'MSFT', 'GOOGL']
    
    print("\n=== Testing Price Fetcher ===\n")
    
    for ticker in test_tickers:
        print(f"\n{ticker}:")
        
        # Current price
        price = fetcher.get_current_price(ticker)
        print(f"  Current Price: ${price:.2f}" if price else "  Price not available")
        
        # Stock info
        info = fetcher.get_stock_info(ticker)
        if info.get('market_cap'):
            print(f"  Market Cap: ${info['market_cap']:,.0f}")
            print(f"  Sector: {info.get('sector', 'N/A')}")
        
        # Historical returns (last 30 days)
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        returns = fetcher.calculate_returns(ticker, start_date)
        if returns is not None:
            print(f"  30-Day Return: {returns*100:.2f}%")
    
    # Batch prices
    print("\n\nBatch Price Fetch:")
    prices = fetcher.get_batch_prices(test_tickers)
    for ticker, price in prices.items():
        print(f"  {ticker}: ${price:.2f}")


if __name__ == "__main__":
    main()
