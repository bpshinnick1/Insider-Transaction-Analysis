# Quick Start Guide

Get the Insider Trading Bot up and running in 15 minutes!

## Prerequisites

- Python 3.8+
- Interactive Brokers account with TWS/IB Gateway
- Git

## Installation (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/insider-trading-bot.git
cd insider-trading-bot

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up configuration
cp config/.env.example config/.env
# Edit config/.env with your settings

# 5. Initialize database
python src/utils/database.py
```

## Configure IBKR (5 minutes)

1. **Start TWS or IB Gateway**

2. **Enable API Access**:
   - Go to: File → Global Configuration → API → Settings
   - ✅ Enable ActiveX and Socket Clients
   - ✅ Read-Only API: OFF
   - Trusted IPs: Add `127.0.0.1`
   - Socket Port: `7497` (paper) or `7496` (live)
   - Click OK and restart

3. **Test Connection**:
```bash
python src/trading/ibkr_client.py
```

## Run Your First Trade Cycle (5 minutes)

### Step 1: Collect Data
```bash
python src/data_collection/scraper.py
```
Expected output: "Scraped X transactions"

### Step 2: Generate Signals
```bash
python src/analysis/signal_generator.py
```
Expected output: "Generated X new signals"

### Step 3: Paper Trade (Recommended)
```bash
python src/trading/trader.py --mode paper
```

## Automated Mode

Run continuously with scheduled data collection:

```bash
python main.py
```

The bot will:
- Scrape insider data every 4 hours
- Generate signals automatically
- Execute trades based on signals
- Manage existing positions

Press `Ctrl+C` to stop.

## Quick Commands Reference

```bash
# Data collection
python src/data_collection/scraper.py

# Generate signals
python src/analysis/signal_generator.py

# Backtest strategy
python src/analysis/backtester.py --start-date 2020-01-01 --end-date 2024-12-31

# Paper trading
python src/trading/trader.py --mode paper

# Live trading (⚠️ USE WITH CAUTION)
python src/trading/trader.py --mode live

# Automated scheduling
python main.py

# Run tests
pytest tests/ -v

# View performance
jupyter notebook notebooks/performance_analysis.ipynb
```

## Project Structure

```
insider-trading-bot/
├── src/
│   ├── data_collection/    # Web scraping & data fetching
│   ├── analysis/            # Signal generation & backtesting
│   ├── trading/             # IBKR integration & execution
│   └── utils/               # Database, logging, config
├── tests/                   # Unit tests
├── data/                    # Data storage
├── logs/                    # Application logs
├── config/                  # Configuration files
├── notebooks/               # Jupyter analysis notebooks
└── main.py                  # Automated scheduler
```

## Configuration Essentials

Edit `config/.env`:

```env
# Trading Mode
PAPER_TRADING=True        # Set False for live trading

# IBKR Connection
IBKR_PORT=7497           # 7497=paper, 7496=live

# Signal Criteria
MIN_TRANSACTION_VALUE=100000  # $100k minimum insider purchase

# Position Sizing
POSITION_SIZE_PCT=0.02   # 2% of portfolio per trade
MAX_POSITIONS=10         # Maximum concurrent positions

# Risk Management
STOP_LOSS_PCT=0.03       # 3% stop loss
PROFIT_TARGET_PCT=0.06   # 6% profit target
HOLD_PERIOD_DAYS=10      # Default holding period

# Data Collection
SCRAPE_INTERVAL_HOURS=4  # How often to check for new data
```

## Verification Checklist

Before running in live mode:

- [ ] Paper trading tested successfully
- [ ] Configuration reviewed and appropriate
- [ ] Risk limits set correctly
- [ ] Stop losses configured
- [ ] Position sizes are reasonable
- [ ] Database initialized
- [ ] Logs are being written
- [ ] IBKR connection stable

## Common Issues & Solutions

### "Cannot connect to IBKR"
- Ensure TWS/Gateway is running
- Check API is enabled in settings
- Verify correct port (7497 vs 7496)
- Restart TWS/Gateway

### "No transactions found"
- OpenInsider may be temporarily unavailable
- Check internet connection
- Try again in a few minutes

### "Module not found"
- Activate virtual environment: `source venv/bin/activate`
- Reinstall requirements: `pip install -r requirements.txt`

## Next Steps

1. **Monitor for 1-2 weeks** in paper trading mode
2. **Review performance** using `notebooks/performance_analysis.ipynb`
3. **Adjust parameters** based on results
4. **Run backtests** to validate strategy
5. **Gradually increase** position sizes if comfortable

## Safety Reminders

⚠️ **IMPORTANT**:
- Always start with **paper trading**
- Set **strict risk limits**
- Never risk more than you can afford to lose
- Monitor positions daily
- Keep detailed logs

## Need Help?

1. Check full documentation in `docs/SETUP.md`
2. Review logs: `logs/trading_bot.log`
3. Run tests: `pytest tests/ -v`
4. Consult [IBKR API docs](https://interactivebrokers.github.io/tws-api/)

---

**Ready to start?** Run the test connection and begin paper trading!

```bash
python src/trading/ibkr_client.py && python src/trading/trader.py --mode paper
```
