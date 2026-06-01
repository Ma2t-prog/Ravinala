# Docker Deployment

Complete containerized setup for Ravinala platform.

## Services

- **PostgreSQL 15** (TimescaleDB): Database
- **Redis 7**: Cache layer
- **FastAPI Backend**: Financial services API
- **React Frontend**: Interactive terminal

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- 4GB+ available RAM
- 10GB+ free disk space

### Setup

1. Create environment file:
```bash
cp ../../.env.example .env
```

2. Start all services:
```bash
docker-compose up -d
```

3. Monitor startup (30-60 seconds):
```bash
docker-compose logs -f
```

4. Verify services are healthy:
```bash
docker-compose ps
```

All services should show "Up" status.

## Access

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | Web application |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| API ReDoc | http://localhost:8000/redoc | Alternative docs |
| Agent Monitor | http://localhost:5173/agents/monitor | Agent dashboard |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache |

## Common Commands

### Start services
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Restart a service
```bash
docker-compose restart backend
```

### Execute commands in container
```bash
# Backend shell
docker exec -it ravinala_backend sh

# Database query
docker exec ravinala_postgres psql -U ravinala -d ravinala -c "SELECT version();"
```

### View resource usage
```bash
docker stats ravinala_backend ravinala_frontend ravinala_postgres ravinala_redis
```

## Database Management

### Backup database
```bash
docker exec ravinala_postgres pg_dump -U ravinala ravinala > backup.sql
```

### Restore database
```bash
docker exec -i ravinala_postgres psql -U ravinala ravinala < backup.sql
```

### Connect to database
```bash
docker exec -it ravinala_postgres psql -U ravinala -d ravinala
```

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs backend

# Rebuild images
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Port conflicts
If ports are already in use, modify docker-compose.yml:
```yaml
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

### Database issues
```bash
# Reset database (WARNING: deletes data)
docker-compose down
rm -rf volumes/
docker-compose up -d
```

### Out of memory
Increase Docker memory limit in Docker Desktop preferences.

## Environment Variables

See `../../.env.example` for all available variables. Key ones:
```
DATABASE_URL=postgresql://ravinala:ravinala@postgres:5432/ravinala
REDIS_URL=redis://redis:6379/0
DEBUG=false
ENVIRONMENT=production
```

## Production Considerations

For production deployment:
1. Use strong `DB_PASSWORD` and `DB_USER`
2. Set `DEBUG=false` nd `ENVIRONMENT=production`
3. Configure SSL/TLS for frontend and API
4. Set up proper monitoring and logging
5. Use managed database services (AWS RDS, etc.)
6. Implement auto-scaling policies
7. Configure CI/CD pipeline

## Logs

Application logs are stored in:
- Backend: `../../montecarlo/backend/logs/`
- Docker container: `docker logs ravinala_backend`

View real-time logs:
```bash
docker-compose logs -f --since 5m
```

## Performance Tips

1. Keep Docker images small (use alpine when possible)
2. Mount volumes for persistent data only
3. Use Docker named volumes vs. bind mounts
4. Configure health checks for all services
5. Set resource limits on containers
6. Use connection pooling for database

## Network Architecture

All services communicate through `ravinala_network` bridge:
```
Frontend (5173) ←→ Backend (8000) ←→ PostgreSQL (5432)
                                   ↓
                              Redis (6379)
```

## Security Notes

- Default credentials are for development only
- Change passwords in production `.env`
- SSL/TLS not configured by default
- Database port is exposed for debugging (restrict in production)
- Use secrets management (Docker Secrets, Vault) in production

---

For local development and testing, this setup is production-ready. Adjust for your specific hosting environment (AWS, Azure, GCP, Kubernetes, etc.).
