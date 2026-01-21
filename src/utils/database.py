"""
Database module for storing insider transactions and trading signals.
Uses SQLite for local storage with SQLAlchemy ORM.
"""

import os
from datetime import datetime
from typing import List, Optional
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

Base = declarative_base()


class InsiderTransaction(Base):
    """Store raw insider transaction data."""
    __tablename__ = 'insider_transactions'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String, nullable=False, index=True)
    company_name = Column(String)
    insider_name = Column(String, nullable=False)
    insider_title = Column(String)  # CEO, CFO, Director, etc.
    transaction_date = Column(DateTime, nullable=False, index=True)
    filing_date = Column(DateTime, nullable=False)
    transaction_type = Column(String)  # P-Purchase, S-Sale, etc.
    shares = Column(Float)
    price_per_share = Column(Float)
    total_value = Column(Float, nullable=False)
    shares_owned_after = Column(Float)
    is_10b5_1_plan = Column(Boolean, default=False)
    sec_form_url = Column(String)
    data_hash = Column(String, unique=True)  # For deduplication
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<InsiderTransaction({self.ticker}, {self.insider_name}, ${self.total_value:,.0f})>"


class TradingSignal(Base):
    """Store generated trading signals."""
    __tablename__ = 'trading_signals'
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(String, unique=True, nullable=False)  # UUID
    ticker = Column(String, nullable=False, index=True)
    transaction_id = Column(Integer)  # Link to InsiderTransaction
    signal_date = Column(DateTime, nullable=False, index=True)
    signal_strength = Column(String)  # HIGH, MEDIUM, LOW
    conviction_score = Column(Float)  # 0-100
    entry_price = Column(Float)
    target_position_size = Column(Integer)  # Number of shares
    stop_loss = Column(Float)
    profit_target = Column(Float)
    status = Column(String, default='ACTIVE')  # ACTIVE, EXECUTED, EXPIRED, CANCELLED
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TradingSignal({self.ticker}, {self.signal_strength}, ${self.entry_price:.2f})>"


class Trade(Base):
    """Store executed trades and their outcomes."""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(String)  # Link to TradingSignal
    ticker = Column(String, nullable=False, index=True)
    entry_date = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    shares = Column(Integer, nullable=False)
    exit_date = Column(DateTime)
    exit_price = Column(Float)
    exit_reason = Column(String)  # STOP_LOSS, PROFIT_TARGET, TIME_BASED, MANUAL
    gross_pnl = Column(Float)
    net_pnl = Column(Float)  # After commissions and fees
    return_pct = Column(Float)
    commission = Column(Float, default=0.0)
    status = Column(String, default='OPEN')  # OPEN, CLOSED
    ibkr_order_id = Column(String)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Trade({self.ticker}, {self.shares} shares @ ${self.entry_price:.2f})>"


class Portfolio(Base):
    """Track portfolio positions and performance."""
    __tablename__ = 'portfolio'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    cash = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    num_positions = Column(Integer, default=0)
    daily_pnl = Column(Float)
    cumulative_return = Column(Float)
    spy_price = Column(Float)  # For benchmark comparison
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Portfolio(${self.total_value:,.2f}, {self.num_positions} positions)>"


class Database:
    """Database manager for the trading bot."""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection."""
        if db_path is None:
            db_path = os.getenv('DATABASE_PATH', 'data/trading_bot.db')
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def add_transaction(self, transaction_data: dict) -> Optional[InsiderTransaction]:
        """Add a new insider transaction to the database."""
        try:
            transaction = InsiderTransaction(**transaction_data)
            self.session.add(transaction)
            self.session.commit()
            return transaction
        except sa.exc.IntegrityError:
            # Transaction already exists (duplicate hash)
            self.session.rollback()
            return None
        except Exception as e:
            self.session.rollback()
            raise e
    
    def add_signal(self, signal_data: dict) -> TradingSignal:
        """Add a new trading signal."""
        signal = TradingSignal(**signal_data)
        self.session.add(signal)
        self.session.commit()
        return signal
    
    def add_trade(self, trade_data: dict) -> Trade:
        """Add a new trade."""
        trade = Trade(**trade_data)
        self.session.add(trade)
        self.session.commit()
        return trade
    
    def update_trade(self, trade_id: int, **kwargs) -> Trade:
        """Update an existing trade."""
        trade = self.session.query(Trade).filter_by(id=trade_id).first()
        if trade:
            for key, value in kwargs.items():
                setattr(trade, key, value)
            trade.updated_at = datetime.utcnow()
            self.session.commit()
        return trade
    
    def get_recent_transactions(self, days: int = 7) -> List[InsiderTransaction]:
        """Get insider transactions from the last N days."""
        cutoff = datetime.utcnow() - pd.Timedelta(days=days)
        return self.session.query(InsiderTransaction).filter(
            InsiderTransaction.filing_date >= cutoff
        ).order_by(InsiderTransaction.filing_date.desc()).all()
    
    def get_active_signals(self) -> List[TradingSignal]:
        """Get all active trading signals."""
        return self.session.query(TradingSignal).filter_by(status='ACTIVE').all()
    
    def get_open_trades(self) -> List[Trade]:
        """Get all currently open trades."""
        return self.session.query(Trade).filter_by(status='OPEN').all()
    
    def get_all_trades(self) -> List[Trade]:
        """Get all trades for analysis."""
        return self.session.query(Trade).all()
    
    def add_portfolio_snapshot(self, snapshot_data: dict) -> Portfolio:
        """Add a portfolio snapshot."""
        snapshot = Portfolio(**snapshot_data)
        self.session.add(snapshot)
        self.session.commit()
        return snapshot
    
    def close(self):
        """Close database connection."""
        self.session.close()


# Import pandas here to avoid circular dependency
import pandas as pd


if __name__ == "__main__":
    # Initialize database
    print("Initializing database...")
    db = Database()
    print(f"Database created at: {db.db_path}")
    print("Tables created:")
    print("  - insider_transactions")
    print("  - trading_signals")
    print("  - trades")
    print("  - portfolio")
    print("\nDatabase ready!")
