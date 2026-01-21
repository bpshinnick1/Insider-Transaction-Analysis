# Setup Guide

## Prerequisites

Before setting up the Insider Trading Bot, ensure you have:

1. **Python 3.8 or higher** installed
2. **Interactive Brokers account** (paper or live)
3. **TWS or IB Gateway** installed and configured
4. **Git** for version control

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/insider-trading-bot.git
cd insider-trading-bot
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate on macOS/Linux
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Interactive Brokers

#### Install TWS or IB Gateway

1. Download from [Interactive Brokers](https://www.interactivebrokers.com/en/trading/tws.php)
2. Install and log in to your account

#### Enable API Access

1. In TWS/Gateway, go to **File → Global Configuration → API → Settings**
2. **Enable ActiveX and Socket Clients**
3. **Trusted IP Addresses**: Add `127.0.0.1`
4. **Socket Port**: Note the port (7497 for paper, 7496 for live)
5. **Master API Client ID**: Leave as default or note if changed
6. Click **OK** and restart TWS/Gateway

### 5. Configure Environment Variables

```bash
# Copy the example environment file
cp config/.env.example config/.env

# Edit the configuration
nano config/.env  # or use your preferred editor
```

Update the following settings:

```env
# Paper trading (recommended for testing)
PAPER_TRADING=True
IBKR_PORT=7497  # 7497 for paper, 7496 for live

# Trading parameters
MIN_TRANSACTION_VALUE=100000  # $100k minimum
POSITION_SIZE_PCT=0.02  # 2% per position
MAX_POSITIONS=10

# Risk management
STOP_LOSS_PCT=0.03  # 3% stop loss
PROFIT_TARGET_PCT=0.06  # 6% profit target
HOLD_PERIOD_DAYS=10

# SEC EDGAR (required)
SEC_USER_AGENT=YourName your@email.com
```

### 6. Initialize Database

```bash
python src/utils/database.py
```

You should see:
```
Initializing database...
Database created at: data/trading_bot.db
Tables created:
  - insider_transactions
  - trading_signals
  - trades
  - portfolio

Database ready!
```

### 7. Test Connection to IBKR

```bash
# Make sure TWS/Gateway is running first!
python src/trading/ibkr_client.py
```

Expected output:
```
=== Testing IBKR Connection ===

✓ Connected successfully

Account Summary:
  NetLiquidation: $1,000,000.00
  TotalCashValue: $1,000,000.00
  BuyingPower: $4,000,000.00

No current positions

AAPL Current Price: $178.50

✓ Disconnected
```

If you see errors, check:
- TWS/Gateway is running
- API is enabled in settings
- Port number matches configuration
- Firewall isn't blocking connection

### 8. Test Data Collection

```bash
python src/data_collection/scraper.py
```

This will scrape recent insider transactions from OpenInsider.

### 9. Generate Signals

```bash
python src/analysis/signal_generator.py
```

This will analyze transactions and generate trading signals.

## Running the Bot

### Option 1: Manual Mode (One-time run)

```bash
# Scrape data
python src/data_collection/scraper.py

# Generate signals
python src/analysis/signal_generator.py

# Execute trades (paper trading)
python src/trading/trader.py --mode paper
```

### Option 2: Automated Mode (Scheduled)

```bash
# Runs continuously with scheduled tasks
python main.py
```

This will:
- Scrape insider data every 4 hours (configurable)
- Generate signals automatically
- Monitor and manage positions

Press `Ctrl+C` to stop.

### Option 3: Backtest Mode

```bash
python src/analysis/backtester.py --start-date 2020-01-01 --end-date 2024-12-31
```

## Verification Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed (`pip list` shows required packages)
- [ ] `.env` file configured with your settings
- [ ] Database initialized (`data/trading_bot.db` exists)
- [ ] TWS/IB Gateway running with API enabled
- [ ] Connection test successful
- [ ] Data scraper runs without errors
- [ ] Signal generator works
- [ ] Paper trading mode tested

## Common Issues

### Cannot connect to IBKR

**Problem**: `ConnectionRefusedError` or timeout

**Solutions**:
1. Ensure TWS/Gateway is running
2. Check API is enabled: File → Global Configuration → API → Settings
3. Verify port number matches (7497 for paper, 7496 for live)
4. Add 127.0.0.1 to trusted IPs
5. Restart TWS/Gateway after changing settings

### Module not found errors

**Problem**: `ModuleNotFoundError`

**Solutions**:
1. Ensure virtual environment is activated
2. Install requirements: `pip install -r requirements.txt`
3. Check Python version: `python --version` (should be 3.8+)

### Database errors

**Problem**: SQLAlchemy or database errors

**Solutions**:
1. Delete old database: `rm data/trading_bot.db`
2. Reinitialize: `python src/utils/database.py`

### Scraper returns no data

**Problem**: OpenInsider scraper returns empty results

**Solutions**:
1. Check internet connection
2. OpenInsider might be temporarily down
3. Try again in a few minutes
4. Check logs for specific errors

## Next Steps

1. **Test in Paper Trading**: Run the bot for several days in paper mode
2. **Monitor Performance**: Check logs and database for trade results
3. **Adjust Parameters**: Tune settings in `.env` based on results
4. **Run Backtests**: Test historical performance
5. **Review and Iterate**: Analyze results and improve strategy

## Security Reminders

- **Never commit `.env`** file to version control
- **Start with paper trading** before risking real money
- **Set strict risk limits** in configuration
- **Monitor positions** daily
- **Keep API credentials secure**

## Support

For issues or questions:
1. Check the documentation in `docs/`
2. Review logs in `logs/trading_bot.log`
3. Open an issue on GitHub
4. Consult Interactive Brokers API documentation

---

**Ready to trade?** Make sure you've completed all setup steps and tested thoroughly in paper mode first!
