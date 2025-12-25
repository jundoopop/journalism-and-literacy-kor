#!/bin/bash
# Run all tests for News Literacy Highlighting System

set -e

echo "=========================================="
echo " News Literacy System - Test Runner"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}pytest not found. Installing test dependencies...${NC}"
    pip install -q pytest pytest-cov pytest-mock pytest-asyncio
fi

# Run unit tests
echo -e "${YELLOW}Running unit tests...${NC}"
pytest tests/unit -v -m "not slow" || {
    echo -e "${RED}Unit tests failed!${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}✓ Unit tests passed${NC}"
echo ""

# Run integration tests
echo -e "${YELLOW}Running integration tests...${NC}"
pytest tests/integration -v || {
    echo -e "${RED}Integration tests failed!${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}✓ Integration tests passed${NC}"
echo ""

# Run all tests with coverage
echo -e "${YELLOW}Running all tests with coverage...${NC}"
pytest tests/ --cov=scripts --cov-report=term-missing --cov-report=html || {
    echo -e "${RED}Coverage tests failed!${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}=========================================="
echo " All tests passed! ✓"
echo "==========================================${NC}"
echo ""
echo "Coverage report generated in: htmlcov/index.html"
