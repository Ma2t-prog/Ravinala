# Ravinala - Quick Start (2 minutes)

## For Recruiters

Want to test this project? Follow these 3 steps:

### 1. Prerequisites
- Docker Desktop (https://www.docker.com/products/docker-desktop)
- Git

### 2. Clone & Run
```bash
git clone https://github.com/Ma2t-prog/Ravinala.git
cd Ravinala/montecarlo/deployment
docker-compose up -d
```

Wait 30-60 seconds for services to start.

### 3. Access

| What | URL |
|------|-----|
| Web App | http://localhost:5173 |
| API (Swagger) | http://localhost:8000/docs |
| Agent Dashboard | http://localhost:5173/agents/monitor |

### Verify Everything Works

**Windows:**
```bash
.\verify.bat
```

**Mac/Linux:**
```bash
bash verify.sh
```

Should show "All tests passed!"

---

## Stop Services
```bash
docker-compose down
```

---

## What You're Looking At

- **Frontend**: React/TypeScript interactive financial terminal
- **Backend**: FastAPI with autonomous LangGraph agents
- **Database**: PostgreSQL with TimescaleDB
- **Cache**: Redis for real-time data
- **Architecture**: Production-grade, fully containerized

---

## Learn More

- `README.md` - Full project overview
- `STRUCTURE.md` - Code organization
- `INSTALLATION_GUIDE.md` - Detailed setup guide
- `montecarlo/README_OMEGA.md` - Backend documentation

---

Questions? Check the docs or see the code on GitHub: https://github.com/Ma2t-prog/Ravinala
