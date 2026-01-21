# insider-trading-bot
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python-based automated trading system that scrapes insider trading data from OpenInsider, analyzes significant insider purchases, and executes trades via Interactive Brokers API.

## 🎯 Project Overview

This bot monitors SEC Form 4 filings to identify significant insider buying activity (transactions >£100k by CEOs, CFOs, and Directors) and automatically executes paper trades or live positions through Interactive Brokers. The system demonstrates proficiency in:

- **Data Engineering**: Web scraping, data cleaning, and ETL pipelines
- **Financial Analysis**: Rule-based trading signals, backtesting, and performance metrics
- **API Integration**: Interactive Brokers API (IBKR) for automated trade execution
- **Software Engineering**: Production-ready code with testing, logging, and error handling

## 🏗️ Architecture

```
┌─────────────────┐      ┌──────────────┐      ┌─────────────┐
│  OpenInsider    │ ───> │   Pipeline   │ ───> │   SQLite    │
│  SEC EDGAR      │      │   Scraper    │      │   Database  │
└─────────────────┘      └──────────────┘      └─────────────┘
                                                       │
                                                       ▼
┌─────────────────┐      ┌──────────────┐      ┌─────────────┐
│  IBKR Trading   │ <─── │   Trading    │ <─── │   Signal    │
│   Platform      │      │   Engine     │      │  Generator  │
└─────────────────┘      └──────────────┘      └─────────────┘
                                                       │
                                                       ▼
                         ┌──────────────┐      ┌─────────────┐
                         │  Backtesting │      │  yfinance   │
                         │    Engine    │ <─── │   Data      │
                         └──────────────┘      └─────────────┘
```

## 🚀 Key Features

### Data Collection
- **Automated scraping** of OpenInsider for real-time insider transaction data
- **SEC EDGAR API integration** for Form 4 filing retrieval
- **Intelligent filtering**: CEO/CFO/Director purchases only, excluding 10b5-1 plans
- **Deduplication logic** to prevent duplicate signal processing
- **Price data integration** via yfinance for performance tracking

### Trading Logic
- **Rule-based signals**: Transactions >£100k trigger buy signals
- **Multiple insider clustering**: Enhanced conviction when multiple insiders buy within 30 days
- **Market regime detection**: Volatility and momentum filters
- **Position sizing**: Dynamic allocation based on conviction score
- **Risk management**: Stop-loss (-3%), profit target (+6%), time-based exits (10 days)

### Execution & Monitoring
- **IBKR API integration** using ib_insync library
- **Paper trading mode** for safe testing
- **Real-time order management**: Limit orders, fill tracking, error handling
- **Position management**: Automated entries and rule-based exits
- **Comprehensive logging**: All actions logged with timestamps and details

### Backtesting & Analysis
- **Historical performance analysis** with realistic slippage and fees
- **Benchmark comparison**: S&P 500 (SPY) performance tracking
- **Risk metrics**: Sharpe ratio, max drawdown, win rate, average return
- **Walk-forward validation** to prevent overfitting
- **Parameter optimization** for rule refinement

## 📋 Requirements

### System Requirements
- Python 3.8 or higher
- Interactive Brokers account (paper or live)
- TWS or IB Gateway running locally

### Python Dependencies
```
pandas>=1.3.0
numpy>=1.21.0
yfinance>=0.1.70
requests>=2.26.0
beautifulsoup4>=4.10.0
lxml>=4.9.0
ib_insync>=0.9.70
sqlalchemy>=1.4.0
python-dotenv>=0.19.0
schedule>=1.1.0
pytest>=7.0.0
```

## 🔧 Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/insider-trading-bot.git
cd insider-trading-bot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp config/.env.example config/.env
# Edit .env with your IBKR credentials and preferences
```

5. **Initialize database**
```bash
python src/utils/database.py
```

## ⚙️ Configuration

Edit `config/.env`:

```env
# IBKR Configuration
IBKR_HOST=127.0.0.1
IBKR_PORT=7497  # 7497 for paper trading, 7496 for live
IBKR_CLIENT_ID=1
PAPER_TRADING=True

# Trading Parameters
MIN_TRANSACTION_VALUE=100000  # Minimum insider purchase value (£100k)
POSITION_SIZE_PCT=0.02  # 2% of portfolio per position
MAX_POSITIONS=10
STOP_LOSS_PCT=0.03  # 3% stop loss
PROFIT_TARGET_PCT=0.06  # 6% profit target
HOLD_PERIOD_DAYS=10

# Data Collection
SCRAPE_INTERVAL_HOURS=4
LOOKBACK_DAYS=7

# Risk Management
MAX_DAILY_TRADES=5
MAX_PORTFOLIO_EXPOSURE=0.20
```

## 🎮 Usage

### 1. Data Collection (Manual Run)
```bash
python src/data_collection/scraper.py
```

### 2. Generate Trading Signals
```bash
python src/analysis/signal_generator.py
```

### 3. Backtesting
```bash
python src/analysis/backtester.py --start-date 2020-01-01 --end-date 2024-12-31
```

### 4. Paper Trading (Live)
```bash
# Ensure TWS/IB Gateway is running
python src/trading/trader.py --mode paper
```

### 5. Automated Scheduling
```bash
python main.py
```

## 📊 Example Output

### Signal Generation
```
[2024-01-15 10:30:45] INFO: New insider purchase detected
Ticker: AAPL
Insider: Tim Cook (CEO)
Transaction Value: $2,500,000
Shares: 15,000
Date: 2024-01-14
Signal Strength: HIGH (CEO, large purchase)
Action: BUY signal generated
```

### Backtesting Results
```
=== Backtest Results (2020-2024) ===
Total Trades: 247
Winning Trades: 156 (63.2%)
Average Return: 4.8%
Max Drawdown: -12.3%
Sharpe Ratio: 1.42
Total Return: 89.7%
SPY Return: 67.3%
Alpha: +22.4%
```

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

## 📁 Project Structure

```
insider-trading-bot/
│
├── src/
│   ├── data_collection/
│   │   ├── scraper.py              # OpenInsider web scraping
│   │   ├── sec_edgar.py            # SEC EDGAR API client
│   │   └── price_fetcher.py        # yfinance price data
│   │
│   ├── analysis/
│   │   ├── signal_generator.py     # Trading signal logic
│   │   ├── backtester.py           # Backtesting engine
│   │   └── performance_metrics.py  # Analytics and reporting
│   │
│   ├── trading/
│   │   ├── trader.py               # Main trading bot
│   │   ├── ibkr_client.py          # IBKR API wrapper
│   │   ├── position_manager.py     # Position tracking
│   │   └── risk_manager.py         # Risk controls
│   │
│   └── utils/
│       ├── database.py             # SQLite database operations
│       ├── logger.py               # Logging configuration
│       └── config.py               # Configuration loader
│
├── tests/
│   ├── test_scraper.py
│   ├── test_signals.py
│   └── test_backtester.py
│
├── data/
│   ├── raw/                        # Raw scraped data
│   └── processed/                  # Cleaned data
│
├── config/
│   ├── .env.example                # Template configuration
│   └── trading_rules.yaml          # Trading rule definitions
│
├── notebooks/
│   ├── exploratory_analysis.ipynb  # Data exploration
│   └── performance_review.ipynb    # Results visualization
│
├── logs/                           # Application logs
├── docs/                           # Additional documentation
├── requirements.txt                # Python dependencies
├── main.py                         # Entry point for scheduled bot
└── README.md                       # This file
```

## 🔒 Security Considerations

- **Never commit API keys** or credentials (use `.env`)
- **Paper trade first** before risking real capital
- **Monitor positions** regularly
- **Set strict risk limits** in configuration
- **Review all signals** before automation

## 📈 Performance Tracking

The bot tracks and logs:
- Individual trade P&L
- Win rate and average return
- Drawdown analysis
- Comparison to SPY benchmark
- Sharpe ratio and risk-adjusted returns

View performance dashboard:
```bash
jupyter notebook notebooks/performance_review.ipynb
```

## 🛠️ Development Roadmap

- [ ] Machine learning signal enhancement
- [ ] Multi-factor analysis (momentum, value, sentiment)
- [ ] Advanced order types (trailing stops, bracket orders)
- [ ] Real-time alerts (Telegram/Slack integration)
- [ ] Portfolio optimization (Modern Portfolio Theory)
- [ ] Options trading integration
- [ ] Cloud deployment (AWS Lambda scheduling)

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. It is not financial advice. Trading stocks involves risk of loss. The author is not responsible for any financial losses incurred through use of this software.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

Ben - [Your Email/LinkedIn]

Project Link: [https://github.com/yourusername/insider-trading-bot](https://github.com/benpshinnick1/insider-trading-bot)

---

**Built with Python 🐍 | Powered by IBKR API 📈 | Data from OpenInsider 📊**
