# Project Structure

## Overview

```
Ravinala/
├── montecarlo/              # BACKEND - FastAPI financial services
├── ravinala-web/            # FRONTEND - React/Vite interactive terminal
├── docs/                    # Documentation and guides
├── scripts/                 # Utility scripts
├── data/                    # Sample data and assets
├── deployment/              # Docker configuration
├── README.md                # Main documentation
├── STRUCTURE.md             # This file
├── launch.bat               # Windows launcher
└── launch.sh                # Unix launcher
```

## Backend: montecarlo/

Core financial services engine built with FastAPI and Python.

```
montecarlo/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint
│   │   ├── agents/                  # LangGraph autonomous agents
│   │   │   ├── trading_agent.py     # Order execution and rebalancing
│   │   │   ├── research_agent.py    # Fundamental/quantitative analysis
│   │   │   ├── risk_agent.py        # Risk monitoring and hedging
│   │   │   └── compliance_agent.py  # Regulatory checks
│   │   ├── api/                     # REST API endpoints
│   │   │   ├── market.py            # Market data endpoints
│   │   │   ├── derivatives.py       # Pricing endpoints
│   │   │   ├── portfolio.py         # Portfolio management
│   │   │   └── risk.py              # Risk analytics
│   │   ├── models/                  # SQLAlchemy database models
│   │   │   ├── portfolio.py         # Portfolio entities
│   │   │   ├── position.py          # Trading positions
│   │   │   └── transaction.py       # Trade records
│   │   ├── services/                # Business logic layer
│   │   │   ├── pricing.py           # Derivatives pricing
│   │   │   ├── optimization.py      # Portfolio optimization
│   │   │   ├── risk_calc.py         # VaR, Greeks, stress testing
│   │   │   └── market_data.py       # Market data aggregation
│   │   └── ml/                      # Machine learning models
│   │       ├── predictor.py         # Market predictions
│   │       ├── classifier.py        # Signal classification
│   │       └── calibrator.py        # Model calibration
│   ├── tests/                       # Unit and integration tests
│   ├── requirements.txt             # Python dependencies
│   ├── pyproject.toml               # Project metadata
│   ├── ruff.toml                    # Linter configuration
│   └── alembic/                     # Database migrations
├── data/
│   ├── access_log.json              # Access logs
│   ├── sessions.json                # User sessions
│   ├── users.json                   # User data
│   ├── cache/                       # Redis cache
│   └── tradebook/                   # Trade records
├── deployment/
│   ├── docker-compose.yml           # Container orchestration
│   └── schema.sql                   # Database schema
├── logs/                            # Application logs
├── scripts/                         # Utility scripts
└── README_OMEGA.md                  # Backend-specific guide
```

## Frontend: ravinala-web/

Interactive financial terminal built with React, TypeScript, and Vite.

```
ravinala-web/
├── src/
│   ├── pages/                       # React page components
│   │   ├── Home.tsx                 # Dashboard
│   │   ├── derivatives/
│   │   │   ├── CustomProduct.tsx    # Custom payoff builder
│   │   │   ├── OptionsAnalytics.tsx # Options analysis
│   │   │   ├── StructuringSuite.tsx # Structured products
│   │   │   ├── AdvancedExotics.tsx  # Exotic options
│   │   │   ├── MuseumExotics.tsx    # Historical structures
│   │   │   ├── PricingCenter.tsx    # Pricing engine
│   │   │   └── Sandbox.tsx          # Experimental playground
│   │   ├── market/
│   │   │   ├── MarketIntelligencePage.tsx # Market overview
│   │   │   ├── Intelligence.tsx     # News and analysis
│   │   │   ├── FinancialAnalysis.tsx # Statement analysis
│   │   │   └── MarketNews.tsx       # Breaking news
│   │   ├── risk/
│   │   │   ├── RiskPortfolioSuite.tsx # Risk dashboard
│   │   │   ├── VolCalibration.tsx   # Vol surface
│   │   │   ├── MLPricing.tsx        # ML models
│   │   │   └── Backtesting.tsx      # Backtesting engine
│   │   ├── portfolio/
│   │   │   └── PortfolioOptimizer.tsx # Optimization UI
│   │   ├── research/
│   │   │   └── EquityResearch.tsx   # Research analysis
│   │   ├── genesix/                 # Advanced analytics
│   │   ├── compliance/              # Regulatory tools
│   │   └── AgentMonitorPage.tsx     # Agent dashboard
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Layout.tsx           # Main layout wrapper
│   │   │   ├── TopBar.tsx           # Header component
│   │   │   ├── Sidebar.tsx          # Navigation sidebar
│   │   │   └── MarketStrip.tsx      # Market ticker
│   │   ├── ui/
│   │   │   ├── Card.tsx             # Card component
│   │   │   └── Chart.tsx            # Chart wrapper
│   │   └── ...                      # Other shared components
│   ├── hooks/
│   │   ├── useMarketData.ts         # Market data hook
│   │   ├── usePortfolio.ts          # Portfolio hook
│   │   └── ...                      # Custom hooks
│   ├── api/
│   │   ├── client.ts                # HTTP client setup
│   │   └── endpoints.ts             # API endpoints
│   ├── lib/                         # Utility functions
│   ├── assets/                      # Static assets
│   ├── App.tsx                      # App root
│   ├── main.tsx                     # Entry point
│   └── index.css                    # Global styles
├── public/                          # Static files
├── package.json                     # NPM dependencies
├── vite.config.ts                   # Vite configuration
├── tsconfig.json                    # TypeScript config
├── tsconfig.app.json                # App TypeScript config
├── tsconfig.node.json               # Node TypeScript config
├── eslint.config.js                 # Linter configuration
├── REACT_MIGRATION_ULTIMATE.md      # Migration guide
├── MIGRATION-PROMPT.md              # Migration prompt
└── README.md                        # Frontend guide
```

## Documentation: docs/

```
docs/
├── PROJECT_MAP.md                   # High-level project overview
├── INTERVIEW_DEMO_TRADING_ASSISTANT.md
├── MAC_DEMO_SETUP.md
└── OMEGA_COMPLETE_GUIDE.md          # Complete platform guide
```

## Data: data/

```
data/
├── access_log.json                  # Access logs
├── sessions.json                    # Session data
├── users.json                       # User data
├── cache/                           # Redis cache
│   └── test/                        # Test cache
└── universe/                        # Market universe data
```

## Configuration Files

| File | Purpose |
|------|---------|
| `.gitignore` | Git ignore patterns |
| `.env.example` | Environment variables template |
| `requirements.txt` | Python dependencies (backend) |
| `package.json` | NPM dependencies (frontend) |
| `pyproject.toml` | Python project metadata |
| `ruff.toml` | Python linter config |
| `tsconfig.json` | TypeScript config |
| `vite.config.ts` | Vite bundler config |

## Launcher Scripts

| Script | Purpose | OS |
|--------|---------|-----|
| `launch.bat` | Start all services | Windows |
| `launch.sh` | Start all services | Linux/Mac |

## Key Technologies

### Backend Stack
- FastAPI (async framework)
- SQLAlchemy (ORM)
- Pydantic (validation)
- LangGraph (agents)
- PostgreSQL (database)
- Redis (cache)

### Frontend Stack
- React 19 (UI framework)
- TypeScript (type safety)
- Vite (bundler)
- React Query (data fetching)
- Recharts (charting)
- CSS-in-JS (styling)

## Development Workflow

1. Backend: `montecarlo/backend/` - Python services
2. Frontend: `ravinala-web/` - React application
3. Deployment: `montecarlo/deployment/` - Docker setup
4. Documentation: `docs/` - Guides and specs

## File Naming Conventions

- TypeScript/React: `PascalCase.tsx` for components
- Python: `snake_case.py` for modules
- CSS: Inline styles via React or `PascalCase.css`
- Config: lowercase with hyphens

## Clean Architecture Principles

- Separation of concerns (api/services/models)
- No circular dependencies
- Controllers handle HTTP, services handle business logic
- Models define data structures
- Agents handle autonomous operations

---

Last updated: June 2026
