#!/bin/bash

# RAG Configurator - Ingestion & RAG Testing Script
# This script helps you verify ingestion and test RAG functionality

set -e

GATEWAY_URL="http://localhost:8000"
CONFIG_SERVICE_URL="http://localhost:8001"
INGESTION_SERVICE_URL="http://localhost:8002"
RAG_SERVICE_URL="http://localhost:8003"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   RAG Configurator - Ingestion & RAG Testing Script       ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if config_id is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Please provide your config_id as an argument${NC}"
    echo "Usage: ./test_ingestion_and_rag.sh <config_id>"
    echo ""
    echo "To find your config_id:"
    echo "  1. Open MongoDB Express at http://localhost:8081"
    echo "  2. Go to 'rag_configurator' database → 'configs' collection"
    echo "  3. Copy the _id field from your config"
    exit 1
fi

CONFIG_ID="$1"

echo -e "${YELLOW}Testing with config_id: ${CONFIG_ID}${NC}"
echo ""

# Function to print section header
print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# 1. Check Ingestion Status
print_header "1. Checking Ingestion Status"
echo "Querying: GET ${GATEWAY_URL}/api/v1/ingest/${CONFIG_ID}/status"
STATUS_RESPONSE=$(curl -s "${GATEWAY_URL}/api/v1/ingest/${CONFIG_ID}/status")
echo "$STATUS_RESPONSE" | jq '.'

STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
TOTAL_FILES=$(echo "$STATUS_RESPONSE" | jq -r '.total_files')
PROCESSED_FILES=$(echo "$STATUS_RESPONSE" | jq -r '.processed_files')
FAILED_FILES=$(echo "$STATUS_RESPONSE" | jq -r '.failed_files')
TOTAL_CHUNKS=$(echo "$STATUS_RESPONSE" | jq -r '.total_chunks')
PROGRESS=$(echo "$STATUS_RESPONSE" | jq -r '.progress')

echo ""
echo -e "${GREEN}Status Summary:${NC}"
echo "  Status: $STATUS"
echo "  Progress: ${PROGRESS}%"
echo "  Files: ${PROCESSED_FILES}/${TOTAL_FILES} processed, ${FAILED_FILES} failed"
echo "  Total Chunks: $TOTAL_CHUNKS"

if [ "$STATUS" == "none" ]; then
    echo -e "\n${YELLOW}⚠ No ingestion has been started for this config.${NC}"
    echo "Start ingestion from the UI at http://localhost:5173"
    exit 0
elif [ "$STATUS" == "pending" ] || [ "$STATUS" == "running" ]; then
    echo -e "\n${YELLOW}⏳ Ingestion is still in progress. Please wait...${NC}"
    echo "You can monitor progress in real-time by running this script again."
elif [ "$STATUS" == "completed" ]; then
    echo -e "\n${GREEN}✓ Ingestion completed successfully!${NC}"
elif [ "$STATUS" == "failed" ]; then
    echo -e "\n${RED}✗ Ingestion failed. Check logs for details.${NC}"
fi

# 2. Get Detailed Statistics
print_header "2. Ingestion Statistics"
echo "Querying: GET ${GATEWAY_URL}/api/v1/ingest/${CONFIG_ID}/stats"
STATS_RESPONSE=$(curl -s "${GATEWAY_URL}/api/v1/ingest/${CONFIG_ID}/stats")
echo "$STATS_RESPONSE" | jq '.'

# 3. Check Ingestion Logs
print_header "3. Recent Ingestion Logs"
echo "Querying: GET ${GATEWAY_URL}/api/v1/ingest/${CONFIG_ID}/logs?limit=5"
LOGS_RESPONSE=$(curl -s "${GATEWAY_URL}/api/v1/ingest/${CONFIG_ID}/logs?limit=5")
echo "$LOGS_RESPONSE" | jq '.logs'

# 4. Verify Data in MongoDB
print_header "4. Data Verification"
echo -e "${YELLOW}To verify ingested data in MongoDB:${NC}"
echo "  1. Open MongoDB Express: http://localhost:8081"
echo "  2. Navigate to 'rag_configurator' database"
echo "  3. Check these collections:"
echo "     • 'documents' - Raw document metadata"
echo "     • 'chunks' - Chunked text with embeddings"
echo "     • 'ingestions' - Ingestion history and status"
if [ "$TOTAL_CHUNKS" -gt 0 ]; then
    echo -e "\n${GREEN}✓ Found ${TOTAL_CHUNKS} chunks in the database${NC}"
fi

# 5. Test RAG Query (only if ingestion completed)
if [ "$STATUS" == "completed" ] && [ "$TOTAL_CHUNKS" -gt 0 ]; then
    print_header "5. Testing RAG Query"

    # Default test query
    TEST_QUERY="${2:-What is this document about?}"

    echo -e "${YELLOW}Test Query: \"${TEST_QUERY}\"${NC}"
    echo "Querying: POST ${GATEWAY_URL}/api/v1/query/"

    QUERY_PAYLOAD=$(jq -n \
        --arg query "$TEST_QUERY" \
        --arg config_id "$CONFIG_ID" \
        '{
            query: $query,
            config_id: $config_id,
            include_sources: true,
            include_debug: true
        }')

    echo ""
    echo "Request payload:"
    echo "$QUERY_PAYLOAD" | jq '.'
    echo ""

    QUERY_RESPONSE=$(curl -s -X POST "${GATEWAY_URL}/api/v1/query/" \
        -H "Content-Type: application/json" \
        -d "$QUERY_PAYLOAD")

    # Check if query was successful
    if echo "$QUERY_RESPONSE" | jq -e '.answer' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ RAG Query Successful!${NC}\n"

        ANSWER=$(echo "$QUERY_RESPONSE" | jq -r '.answer')
        SOURCE_COUNT=$(echo "$QUERY_RESPONSE" | jq -r '.sources | length')
        AGENT_TYPE=$(echo "$QUERY_RESPONSE" | jq -r '.metadata.agent_type')
        DURATION=$(echo "$QUERY_RESPONSE" | jq -r '.metadata.total_duration_ms')

        echo -e "${GREEN}Answer:${NC}"
        echo "$ANSWER"
        echo ""
        echo -e "${GREEN}Metadata:${NC}"
        echo "  Agent Type: $AGENT_TYPE"
        echo "  Duration: ${DURATION}ms"
        echo "  Sources: $SOURCE_COUNT chunks"
        echo ""

        # Show sources
        if [ "$SOURCE_COUNT" -gt 0 ]; then
            echo -e "${GREEN}Source Chunks:${NC}"
            echo "$QUERY_RESPONSE" | jq -r '.sources[] | "  • [\(.source_type)] Score: \(.score) - \(.content[:100])..."'
        fi

        # Show debug info if available
        if echo "$QUERY_RESPONSE" | jq -e '.debug' > /dev/null 2>&1; then
            echo ""
            echo -e "${GREEN}Debug Information:${NC}"
            echo "$QUERY_RESPONSE" | jq '.debug'
        fi
    else
        echo -e "${RED}✗ RAG Query Failed${NC}\n"
        echo "Response:"
        echo "$QUERY_RESPONSE" | jq '.'
    fi

    # 6. Access Sandbox UI
    print_header "6. Interactive Testing"
    echo -e "${YELLOW}For interactive testing, use the Sandbox UI:${NC}"
    echo "  URL: http://localhost:3001"
    echo ""
    echo "In the Sandbox UI, you can:"
    echo "  • Enter your config_id: ${CONFIG_ID}"
    echo "  • Chat with your documents interactively"
    echo "  • See real-time responses with source citations"
    echo "  • Test different queries"

else
    print_header "5. RAG Testing"
    echo -e "${YELLOW}⚠ Cannot test RAG query yet${NC}"
    if [ "$STATUS" != "completed" ]; then
        echo "Reason: Ingestion status is '${STATUS}' (need 'completed')"
    elif [ "$TOTAL_CHUNKS" -eq 0 ]; then
        echo "Reason: No chunks found in database"
    fi
    echo ""
    echo "Wait for ingestion to complete, then run this script again."
fi

# Summary
print_header "Summary"
echo -e "${GREEN}Available Resources:${NC}"
echo "  • Configurator UI: http://localhost:5173"
echo "  • Sandbox UI: http://localhost:3001"
echo "  • MongoDB Express: http://localhost:8081"
echo "  • Redis Commander: http://localhost:8082"
echo "  • Gateway API: http://localhost:8000"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  # Check status"
echo "  curl http://localhost:8000/api/v1/ingest/${CONFIG_ID}/status | jq"
echo ""
echo "  # Get stats"
echo "  curl http://localhost:8000/api/v1/ingest/${CONFIG_ID}/stats | jq"
echo ""
echo "  # Test query"
echo "  curl -X POST http://localhost:8000/api/v1/query/ \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"query\":\"Your question?\",\"config_id\":\"${CONFIG_ID}\"}' | jq"
echo ""
echo -e "${GREEN}Testing complete!${NC}"
