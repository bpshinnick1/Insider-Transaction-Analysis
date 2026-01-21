"""
Interactive Brokers API client wrapper.
Handles connection and order execution via ib_insync.
"""

from ib_insync import IB, Stock, MarketOrder, LimitOrder, util
from typing import Optional, List, Dict
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.logger import setup_logger
from src.utils.config import config

logger = setup_logger('ibkr_client')


class IBKRClient:
    """
    Interactive Brokers API client for trade execution.
    """
    
    def __init__(self):
        """Initialize IBKR client."""
        self.ib = IB()
        self.connected = False
    
    def connect(self) -> bool:
        """
        Connect to Interactive Brokers TWS or Gateway.
        
        Returns:
            True if connected successfully
        """
        try:
            logger.info(f"Connecting to IBKR at {config.ibkr_host}:{config.ibkr_port}")
            
            self.ib.connect(
                host=config.ibkr_host,
                port=config.ibkr_port,
                clientId=config.ibkr_client_id,
                readonly=False
            )
            
            self.connected = True
            
            mode = "PAPER" if config.paper_trading else "LIVE"
            logger.info(f"Connected to IBKR ({mode} trading)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from IBKR."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")
    
    def get_account_summary(self) -> Dict:
        """
        Get account information.
        
        Returns:
            Dictionary with account details
        """
        if not self.connected:
            logger.error("Not connected to IBKR")
            return {}
        
        try:
            account_values = self.ib.accountSummary()
            
            summary = {}
            for item in account_values:
                if item.tag in ['TotalCashValue', 'NetLiquidation', 'BuyingPower']:
                    summary[item.tag] = float(item.value)
            
            logger.debug(f"Account summary: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {}
    
    def get_positions(self) -> List[Dict]:
        """
        Get current positions.
        
        Returns:
            List of position dictionaries
        """
        if not self.connected:
            logger.error("Not connected to IBKR")
            return []
        
        try:
            positions = self.ib.positions()
            
            position_list = []
            for pos in positions:
                position_list.append({
                    'ticker': pos.contract.symbol,
                    'shares': pos.position,
                    'avg_cost': pos.avgCost,
                    'market_value': pos.marketValue,
                    'unrealized_pnl': pos.unrealizedPNL
                })
            
            return position_list
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_market_price(self, ticker: str) -> Optional[float]:
        """
        Get current market price for a ticker.
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Current price or None
        """
        if not self.connected:
            logger.error("Not connected to IBKR")
            return None
        
        try:
            # Create contract
            contract = Stock(ticker, 'SMART', 'USD')
            
            # Qualify contract
            self.ib.qualifyContracts(contract)
            
            # Request market data
            ticker_obj = self.ib.reqMktData(contract)
            
            # Wait for data
            self.ib.sleep(1)
            
            # Get last price
            price = ticker_obj.marketPrice()
            
            # Cancel market data
            self.ib.cancelMktData(contract)
            
            logger.debug(f"{ticker}: ${price:.2f}")
            return price if price > 0 else None
            
        except Exception as e:
            logger.error(f"Error getting market price for {ticker}: {e}")
            return None
    
    def place_market_order(self, ticker: str, shares: int, action: str = 'BUY') -> Optional[Dict]:
        """
        Place a market order.
        
        Args:
            ticker: Stock ticker symbol
            shares: Number of shares
            action: 'BUY' or 'SELL'
        
        Returns:
            Order details or None
        """
        if not self.connected:
            logger.error("Not connected to IBKR")
            return None
        
        try:
            # Create contract
            contract = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            # Create market order
            order = MarketOrder(action, shares)
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            logger.info(f"Placed {action} market order: {ticker} {shares} shares, Order ID: {trade.order.orderId}")
            
            # Wait for fill
            self.ib.sleep(2)
            
            # Get order status
            return self._get_trade_details(trade)
            
        except Exception as e:
            logger.error(f"Error placing market order for {ticker}: {e}")
            return None
    
    def place_limit_order(self, ticker: str, shares: int, limit_price: float, 
                         action: str = 'BUY') -> Optional[Dict]:
        """
        Place a limit order.
        
        Args:
            ticker: Stock ticker symbol
            shares: Number of shares
            limit_price: Limit price
            action: 'BUY' or 'SELL'
        
        Returns:
            Order details or None
        """
        if not self.connected:
            logger.error("Not connected to IBKR")
            return None
        
        try:
            # Create contract
            contract = Stock(ticker, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            
            # Create limit order
            order = LimitOrder(action, shares, limit_price)
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            logger.info(f"Placed {action} limit order: {ticker} {shares} shares @ ${limit_price:.2f}, "
                       f"Order ID: {trade.order.orderId}")
            
            # Wait briefly
            self.ib.sleep(1)
            
            return self._get_trade_details(trade)
            
        except Exception as e:
            logger.error(f"Error placing limit order for {ticker}: {e}")
            return None
    
    def cancel_order(self, order_id: int) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: IBKR order ID
        
        Returns:
            True if cancelled successfully
        """
        if not self.connected:
            logger.error("Not connected to IBKR")
            return False
        
        try:
            # Find the order
            trades = self.ib.openTrades()
            
            for trade in trades:
                if trade.order.orderId == order_id:
                    self.ib.cancelOrder(trade.order)
                    logger.info(f"Cancelled order {order_id}")
                    return True
            
            logger.warning(f"Order {order_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def _get_trade_details(self, trade) -> Dict:
        """Extract details from a trade object."""
        return {
            'order_id': trade.order.orderId,
            'ticker': trade.contract.symbol,
            'action': trade.order.action,
            'shares': trade.order.totalQuantity,
            'status': trade.orderStatus.status,
            'filled': trade.orderStatus.filled,
            'remaining': trade.orderStatus.remaining,
            'avg_fill_price': trade.orderStatus.avgFillPrice,
        }
    
    def get_open_orders(self) -> List[Dict]:
        """
        Get all open orders.
        
        Returns:
            List of order dictionaries
        """
        if not self.connected:
            logger.error("Not connected to IBKR")
            return []
        
        try:
            trades = self.ib.openTrades()
            
            orders = []
            for trade in trades:
                orders.append(self._get_trade_details(trade))
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []


def main():
    """Test IBKR connection."""
    client = IBKRClient()
    
    print("\n=== Testing IBKR Connection ===\n")
    
    # Connect
    if client.connect():
        print("✓ Connected successfully")
        
        # Get account info
        summary = client.get_account_summary()
        if summary:
            print("\nAccount Summary:")
            for key, value in summary.items():
                print(f"  {key}: ${value:,.2f}")
        
        # Get positions
        positions = client.get_positions()
        if positions:
            print("\nCurrent Positions:")
            for pos in positions:
                print(f"  {pos['ticker']}: {pos['shares']} shares @ ${pos['avg_cost']:.2f}")
        else:
            print("\nNo current positions")
        
        # Test market data (paper trading should work)
        test_ticker = 'AAPL'
        price = client.get_market_price(test_ticker)
        if price:
            print(f"\n{test_ticker} Current Price: ${price:.2f}")
        
        # Disconnect
        client.disconnect()
        print("\n✓ Disconnected")
        
    else:
        print("✗ Failed to connect")
        print("\nMake sure:")
        print("  1. TWS or IB Gateway is running")
        print("  2. API connections are enabled in TWS/Gateway settings")
        print("  3. The port number in .env matches TWS/Gateway")


if __name__ == "__main__":
    main()
