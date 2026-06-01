# Installation & Verification Guide

This guide ensures you can run Ravinala from scratch successfully.

## System Requirements

- 4GB RAM minimum (8GB recommended)
- 10GB free disk space
- Internet connection for downloading dependencies
- One of:
  - Docker & Docker Compose (easiest)
  - Python 3.10+ + Node.js 18+ + PostgreSQL 13+ + Redis 6+ (local)

## Method 1: Docker (Recommended - 2 minutes)

### 1. Install Docker
Download and install Docker Desktop from https://www.docker.com/products/docker-desktop

### 2. Clone Repository
```bash
git clone https://github.com/Ma2t-prog/Ravinala.git
cd Ravinala
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env if needed (default values work for local testing)
```

### 4. Start Services
```bash
cd montecarlo/deployment
docker-compose up -d
```

Output:
```
Creating ravinala_postgres ... done
Creating ravinala_redis ... done
Creating ravinala_backend ... done
Creating ravinala_frontend ... done
```

### 5. Verify Services
```bash
# Check container status
docker-compose ps

# Should show 4 containers: postgres, redis, backend, frontend
# All should have status "Up"
```

### 6. Access Application
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs
- Agent Monitor: http://localhost:5173/agents/monitor

### 7. View Logs (if needed)
```bash
# Backend logs
docker logs ravinala_backend

# Frontend logs
docker logs ravinala_frontend

# Database logs
docker logs ravinala_postgres
```

### 8. Stop Services
```bash
docker-compose down
```

---

## Method 2: Local Installation (Advanced - 10 minutes)

### Prerequisites Check

#### Windows
```powershell
python --version           # Should be 3.10+
node --version            # Should be 18+
npm --version             # Should be 9+
```

#### Unix/Mac
```bash
python3 --version         # Should be 3.10+
node --version            # Should be 18+
npm --version             # Should be 9+
```

### 1. Install PostgreSQL (if not installed)

Windows: Download from https://www.postgresql.org/download/windows/
Unix/Mac: `brew install postgresql@15`

Verify:
```bash
psql --version
# Output: psql (PostgreSQL) 13.x or higher
```

### 2. Install Redis (if not installed)

Windows: https://github.com/microsoftarchive/redis/releases
Unix/Mac: `brew install redis`

Verify:
```bash
redis-cli --version
# Output: redis-cli 6.x or higher
```

### 3. Clone Repository
```bash
git clone https://github.com/Ma2t-prog/Ravinala.git
cd Ravinala
```

### 4. Setup Backend

#### Create Virtual Environment
```bash
cd montecarlo/backend

# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Unix/Mac
python3 -m venv .venv
source .venv/bin/activate
```

#### Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Takes 2-3 minutes. You should see:
```
Successfully installed fastapi-0.115.0 uvicorn-0.30.0 sqlalchemy-2.0.0 ...
```

#### Database Setup
```bash
# Create PostgreSQL user and database
psql -U postgres
postgres=# CREATE USER ravinala WITH PASSWORD 'ravinala';
postgres=# CREATE DATABASE ravinala OWNER ravinala;
postgres=# \q

# Run migrations
alembic upgrade head

# Output: Done (version at 0001_initial)
```

#### Configure Environment
```bash
# In montecarlo/backend, create .env file
cp .env.example .env
# Default values work for local testing
```

#### Start Backend Server
```bash
# Make sure Redis is running (redis-server in another terminal)
uvicorn app.main:app --reload --port 8000
```

You should see:
```
Uvicorn running on http://127.0.0.1:8000
Application startup complete
```

### 5. Setup Frontend (in new terminal)

```bash
cd ravinala-web

# Install dependencies
npm install

# Takes 1-2 minutes
# Output: added 500 packages
```

#### Start Frontend Server
```bash
npm run dev
```

You should see:
```
VITE v5.x.x  ready in 234 ms
➜  Local:   http://localhost:5173/
➜  press h to show help
```

### 6. Verify Everything Works

#### Backend API
- Visit http://localhost:8000/docs
- You should see Swagger UI with all endpoints
- Click "Try it out" on any GET endpoint (e.g., `/health`)
- Should return 200 OK

#### Frontend
- Visit http://localhost:5173
- Page should load without errors
- Market data should display at the top
- You should see the sidebar with options

#### Agent Monitor
- Go to http://localhost:5173/agents/monitor
- Should display agent status page

---

## Troubleshooting

### Port Already in Use
```bash
# Check what's using the port
lsof -i :8000      # Unix/Mac
netstat -ano | findstr :8000  # Windows

# Kill the process and restart, or use different port:
uvicorn app.main:app --port 8001
```

### Database Connection Error
```bash
# Verify PostgreSQL is running
psql -U ravinala -d ravinala -c "SELECT 1"
# Should return: 1

# If not, (re)start PostgreSQL:
# Windows: Services > PostgreSQL > Start
# Unix/Mac: brew services start postgresql@15
```

### Redis Connection Error
```bash
# Verify Redis is running
redis-cli ping
# Should return: PONG

# If not:
# Windows: Run redis-server.exe
# Unix/Mac: redis-server
```

### Node Modules Issues
```bash
# Clear cache and reinstall
cd ravinala-web
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Python Dependencies Issue
```bash
# Upgrade pip and retry
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --force-reinstall
```

---

## Performance Verification

### Backend Startup
- Should be ready in < 5 seconds
- Check logs for "Application startup complete"

### Frontend Load Time
- Should load in < 3 seconds
- Check browser Network tab (should be < 500ms for main assets)

### API Response Time
- Market data endpoints: < 100ms
- Portfolio endpoints: < 500ms
- Complex calculations: < 2 seconds

---

## Next Steps

1. Explore the API: http://localhost:8000/docs
2. Read the main README for feature overview
3. Check STRUCTURE.md for code organization
4. Run tests: `pytest montecarlo/backend/tests/`
5. Build frontend: `npm run build`

---

## Support

If you encounter issues:
1. Check this guide's Troubleshooting section
2. Review application logs
3. Ensure all dependencies are installed
4. Verify ports 5173, 8000, 5432, 6379 are available

For technical questions, refer to the architecture docs in `docs/` folder.
