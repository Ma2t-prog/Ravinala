#!/bin/bash
# Verification script for Ravinala deployment
# Run this after docker-compose up -d to verify all services are working

echo "=================================================="
echo "  Ravinala Deployment Verification"
echo "=================================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS="${GREEN}✓${NC}"
FAIL="${RED}✗${NC}"
INFO="${YELLOW}ℹ${NC}"

# Track results
PASSED=0
FAILED=0

# Test function
test_service() {
    local name=$1
    local url=$2
    local expected_code=$3
    
    echo -n "Testing $name ... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$response" -eq "$expected_code" ]; then
        echo -e "$PASS HTTP $response"
        ((PASSED++))
    else
        echo -e "$FAIL HTTP $response (expected $expected_code)"
        ((FAILED++))
    fi
}

# Test port connectivity
test_port() {
    local name=$1
    local port=$2
    
    echo -n "Testing $name on port $port ... "
    
    if nc -z localhost $port 2>/dev/null; then
        echo -e "$PASS Connected"
        ((PASSED++))
    else
        echo -e "$FAIL Connection refused"
        ((FAILED++))
    fi
}

echo -e "${INFO} Service Connectivity"
echo "=================================================="

# Test ports
test_port "Frontend" 5173
test_port "Backend" 8000
test_port "PostgreSQL" 5432
test_port "Redis" 6379

echo ""
echo -e "${INFO} HTTP API Endpoints"
echo "=================================================="

# Test HTTP endpoints
test_service "Frontend" "http://localhost:5173" 200
test_service "Backend Health" "http://localhost:8000/health" 200
test_service "API Docs" "http://localhost:8000/docs" 200
test_service "ReDoc" "http://localhost:8000/redoc" 200

echo ""
echo -e "${INFO} Database Checks"
echo "=================================================="

# Test database
echo -n "Testing PostgreSQL connection ... "
if docker exec ravinala_postgres psql -U ravinala -d ravinala -c "SELECT 1;" &>/dev/null; then
    echo -e "$PASS Connected"
    ((PASSED++))
else
    echo -e "$FAIL Connection failed"
    ((FAILED++))
fi

# Test Redis
echo -n "Testing Redis connection ... "
if docker exec ravinala_redis redis-cli ping &>/dev/null | grep -q PONG; then
    echo -e "$PASS Connected (PONG)"
    ((PASSED++))
else
    echo -e "$FAIL Connection failed"
    ((FAILED++))
fi

echo ""
echo -e "${INFO} Docker Containers"
echo "=================================================="

docker-compose ps | tail -n +2 | while read line; do
    if echo "$line" | grep -q "Up"; then
        echo -e "$PASS $line"
    else
        echo -e "$FAIL $line"
    fi
done

echo ""
echo "=================================================="
echo -e "  Results: ${GREEN}$PASSED passing${NC} / ${RED}$FAILED failing${NC}"
echo "=================================================="
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo ""
    echo "Access the application at:"
    echo "  - Frontend: http://localhost:5173"
    echo "  - Backend API: http://localhost:8000/docs"
    echo "  - Agent Monitor: http://localhost:5173/agents/monitor"
    exit 0
else
    echo -e "${RED}Some tests failed. Check Docker logs:${NC}"
    echo "  docker-compose logs -f"
    exit 1
fi
