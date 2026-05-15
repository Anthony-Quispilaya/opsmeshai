#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting OpsMesh AI with dynamic port allocation...${NC}"

# Find available ports using Node helper
PORTS_JSON=$(node scripts/find-available-ports.mjs)
FRONTEND_PORT=$(node -e 'const p = JSON.parse(process.argv[1]); console.log(p.frontend);' "$PORTS_JSON")
BACKEND_PORT=$(node -e 'const p = JSON.parse(process.argv[1]); console.log(p.backend);' "$PORTS_JSON")

APP_URL="http://localhost:${FRONTEND_PORT}"
API_URL="http://localhost:${BACKEND_PORT}"

echo -e "${GREEN}✓ Frontend port: ${FRONTEND_PORT}${NC}"
echo -e "${GREEN}✓ Backend port: ${BACKEND_PORT}${NC}"
echo -e "${GREEN}✓ App URL: ${APP_URL}${NC}"
echo -e "${GREEN}✓ API URL: ${API_URL}${NC}"
echo ""

# Start database if not running
echo -e "${BLUE}📦 Starting Postgres...${NC}"
docker compose up -d postgres 2>/dev/null || true
sleep 1

# Run migrations
echo -e "${BLUE}🔄 Running database migrations...${NC}"
.venv/bin/alembic -c db/alembic.ini upgrade head > /dev/null 2>&1 || true

# Start backend
echo -e "${BLUE}🔙 Starting backend on port ${BACKEND_PORT}...${NC}"
ALLOWED_ORIGINS="http://localhost:${FRONTEND_PORT}" \
BACKEND_CORS_ORIGINS="http://localhost:${FRONTEND_PORT}" \
ENABLE_INBOUND_AUTO_REPLY=true \
API_URL="${API_URL}" \
.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port ${BACKEND_PORT} &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend PID: ${BACKEND_PID}${NC}"

# Wait for backend to start
sleep 3

# Start frontend
echo -e "${BLUE}🎨 Starting frontend on port ${FRONTEND_PORT}...${NC}"
PORT=${FRONTEND_PORT} \
NEXT_PUBLIC_APP_URL="${APP_URL}" \
NEXT_PUBLIC_API_URL="${API_URL}" \
API_URL="${API_URL}" \
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend PID: ${FRONTEND_PID}${NC}"

# Start Photon bridge
echo -e "${BLUE}📨 Starting Photon bridge on port 8787...${NC}"
set -a
source .env 2>/dev/null || true
set +a
PHOTON_CALLBACK_URL="${API_URL}/api/v1/messaging/photon/events" \
API_URL="${API_URL}" \
npm run photon:bridge &
PHOTON_PID=$!
echo -e "${GREEN}✓ Photon bridge PID: ${PHOTON_PID}${NC}"

# Wait for frontend to start
sleep 3

# Verify both are running
echo ""
echo -e "${BLUE}✅ Services started!${NC}"
echo ""
echo -e "${GREEN}📱 Access the app at: ${APP_URL}${NC}"
echo -e "${GREEN}📚 API docs at: ${API_URL}/docs${NC}"
echo -e "${GREEN}❤️  API health: ${API_URL}/api/v1/health${NC}"
echo ""
echo -e "${BLUE}To stop all services, run:${NC}"
echo "kill ${BACKEND_PID} ${FRONTEND_PID} ${PHOTON_PID}"
echo ""

# Keep script running 
trap "echo ''; echo 'Shutting down...'; kill ${BACKEND_PID} ${FRONTEND_PID} ${PHOTON_PID} 2>/dev/null || true; exit 0" EXIT INT

wait
