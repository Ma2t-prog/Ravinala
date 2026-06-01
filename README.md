# Ravinala

Advanced AI-driven financial platform with autonomous agents for portfolio optimization, derivatives pricing, and real-time market analysis.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](montecarlo/backend/requirements.txt)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue.svg)](ravinala-web/tsconfig.json)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](montecarlo/backend/requirements.txt)
[![React 19](https://img.shields.io/badge/React-19-blue.svg)](ravinala-web/package.json)
[![Docker Ready](https://img.shields.io/badge/Docker-ready-blue.svg)](montecarlo/deployment/docker-compose.yml)

**TL;DR:** Clone → `docker-compose up -d` → http://localhost:5173

See **[QUICKSTART.md](QUICKSTART.md)** for 2-minute setup guide.

## Overview

Ravinala is a production-grade financial terminal built with modern full-stack architecture. It combines machine learning, quantitative finance, and autonomous agents to deliver institutional-grade tools for portfolio management, risk analysis, and derivatives structuring.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React/Vite)                    │
│  - Real-time market data streaming                          │
│  - Interactive derivatives pricing engine                   │
│  - Portfolio optimization interface                         │
│  - Risk dashboard with Greeks analytics                     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket
┌──────────────────────┴──────────────────────────────────────┐
│                  Backend (FastAPI/Python)                   │
├─────────────────────────────────────────────────────────────┤
│ Core Services:                                              │
│  - Market data aggregation and caching                      │
│  - Derivatives pricing (Black-Scholes, Monte Carlo)         │
│  - Portfolio optimization (Mean-Variance, CVaR)             │
│  - Risk calculations (VaR, Greeks, Stress Testing)          │
│  - ML-based market prediction                               │
│                                                             │
│ Autonomous Agents (LangGraph):                              │
│  - Trading Agent: Order execution and strategy rebalancing  │
│  - Research Agent: Fundamental and quantitative analysis    │
│  - Risk Agent: Portfolio risk monitoring and hedging        │
│  - Compliance Agent: Regulatory checks and reporting        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                    Data Layer                               │
├─────────────────────────────────────────────────────────────┤
│ - PostgreSQL (portfolio, positions, audit trails)           │
│ - Redis (market data cache, real-time subsriptions)         │
│ - MLflow (model versioning and experiment tracking)         │
│ - Parquet files (historical data, backtesting)              │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend
- **Framework**: FastAPI 0.115+
- **Agent Framework**: LangGraph with Claude 3.5 Sonnet
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis
- **Task Queue**: Celery + Redis
- **Data Processing**: pandas, numpy, scipy
- **Quantitative**: QuantLib, scikit-learn, statsmodels
- **API**: FastAPI async, Pydantic validation
- **Deployment**: Docker, Alembic migrations

### Frontend
- **Framework**: React 19 with TypeScript
- **Build**: Vite 5.x
- **State**: React Query (TanStack Query)
- **Charting**: Recharts
- **Styling**: CSS-in-JS with inline styles
- **HTTP**: Axios with retry logic
- **Real-time**: WebSocket integration

### Infrastructure
- **Containerization**: Docker / Docker Compose
- **Version Control**: Git
- **Monitoring**: Logging to files and stdout

## Features

### Financial Analysis
- Real-time market data for 50+ global indices
- Multi-asset portfolio construction and analysis
- Advanced screening with 100+ technical indicators
- Fundamental analysis with financial statement parsing

### Derivatives
- Exotic options pricing (Barrier, Asian, Lookback, etc.)
- Custom payoff designer with formula parsing
- Greek sensitivity analysis
- Structured products builder
- Interactive pricing surfaces

### Risk Management
- Value-at-Risk (VaR) calculation across confidence levels
- Stress testing with custom scenarios
- Volatility surface calibration
- Hedging strategy optimization
- Real-time portfolio Greeks

### AI/ML
- Autonomous trading agents with LangGraph
- Natural language processing for market analysis
- ML pricing models for derivatives
- Predictive analytics for market movements
- Backtesting framework with event simulation

### Compliance & Reporting
- ESG scoring and analysis
- Regulatory capital requirements (Basel III)
- Automated report generation
- Audit trail logging
- Data governance framework

## Quick Start

## Quick Start

### Fastest Way: Docker (Recommended)

Requires: Docker and Docker Compose

```bash
# Clone the repository
git clone https://github.com/Ma2t-prog/Ravinala.git
cd Ravinala

# Create .env file
cp .env.example .env

# Start all services (PostgreSQL, Redis, Backend, Frontend)
cd montecarlo/deployment
docker-compose up -d

# Wait for services to initialize (30-60 seconds)
# Access:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

Stop services:
```bash
docker-compose down
```

### Local Installation (Advanced)

Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 13+
- Redis 6+

Clone the repository:
```bash
git clone https://github.com/Ma2t-prog/Ravinala.git
cd Ravinala
```

Setup Backend:
```bash
cd montecarlo/backend

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate      # Unix/Mac
# or
.\.venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Set up database
# (Ensure PostgreSQL is running locally)
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --port 8000
```

Setup Frontend (in new terminal):
```bash
cd ravinala-web

# Install dependencies
npm install

# Start development server
npm run dev
```

Access:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Project Structure

```
Ravinala/
├── montecarlo/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── main.py              # FastAPI application
│   │   │   ├── agents/              # Autonomous agents (LangGraph)
│   │   │   ├── api/                 # API routes
│   │   │   ├── models/              # Database models (SQLAlchemy)
│   │   │   ├── services/            # Business logic
│   │   │   └── ml/                  # Machine learning pipelines
│   │   ├── tests/                   # Backend tests
│   │   ├── requirements.txt         # Python dependencies
│   │   └── pyproject.toml           # Project metadata
│   ├── data/
│   │   ├── cache/                   # Redis cache
│   │   ├── ml_artifacts/            # ML models
│   │   └── tradebook/               # Trade records
│   ├── deployment/
│   │   └── docker-compose.yml       # Container orchestration
│   └── README_OMEGA.md              # Detailed backend docs
│
├── ravinala-web/
│   ├── src/
│   │   ├── pages/                   # React pages (derivatives, risk, etc.)
│   │   ├── components/              # Reusable UI components
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── api/                     # API integration layer
│   │   └── index.css                # Global styles
│   ├── vite.config.ts               # Vite configuration
│   ├── tsconfig.json                # TypeScript config
│   └── package.json                 # NPM dependencies
│
├── docs/                            # Documentation
├── launch.bat                       # Windows launcher
├── launch.sh                        # Unix launcher
└── README.md                        # This file
```

## API Documentation

Once running, access interactive API docs at `/docs` (Swagger UI) or `/redoc` (ReDoc).

Key endpoints:
- `POST /api/portfolio/optimize` - Portfolio optimization
- `GET /api/market/indices` - Market data
- `POST /api/derivatives/price` - Derivatives pricing
- `GET /api/risk/analytics` - Risk metrics
- `POST /api/agents/monitor` - Agent status

## Development

### Code Style
- Backend: PEP 8 with ruff linter
- Frontend: ESLint + Prettier
- Type checking: MyPy (backend), TypeScript (frontend)

### Testing
```bash
# Backend tests
cd montecarlo/backend
pytest

# Frontend tests
cd ravinala-web
npm test
```

### Configuration
Environment variables in `.env`:
```
DATABASE_URL=postgresql://user:password@localhost/ravinala
REDIS_URL=redis://localhost:6379
API_KEY=<claude-key>
```

## Performance Notes

- Market data updates: Sub-100ms latency via WebSocket
- Derivatives pricing: <500ms for exotic options
- Portfolio optimization: <2s for 1000-asset portfolios
- Agent response time: 2-5 seconds depending on analysis depth

## Known Limitations & Future Work

- Limited to US/EU market hours for real-time data
- Monte Carlo simulations capped at 100k paths (configurable)
- Agent models require Claude API key (can switch to local LLMs)
- WebSocket reconnection after network failures in development

## Contributing

For internal use. Contact maintainer for contribution guidelines.

## License

Proprietary - All rights reserved.

## Contact

Developed by Matthias  
For inquiries: tsivahinymatthiaspro@gmail.com

---

Last updated: June 2026
