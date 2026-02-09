#!/bin/bash

# RAG Configurator Demo Seeding Script
# This script sets up demo data for the RAG Configurator platform
# 
# Usage: ./seed-demo.sh [options]
# Options:
#   --gateway-url    Gateway URL (default: http://localhost:8000)
#   --skip-user      Skip user creation (use existing)
#   --help          Show this help message

set -e

# Configuration
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
DEMO_USER_EMAIL="${DEMO_USER_EMAIL:-demo@techcorp.com}"
DEMO_USER_PASSWORD="${DEMO_USER_PASSWORD:-DemoPass123!}"
DEMO_USER_NAME="${DEMO_USER_NAME:-Demo User}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install missing dependencies:"
        log_info "  macOS: brew install curl jq"
        log_info "  Ubuntu/Debian: sudo apt-get install curl jq"
        log_info "  CentOS/RHEL: sudo yum install curl jq"
        exit 1
    fi
    
    log_success "All dependencies found"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --gateway-url)
                GATEWAY_URL="$2"
                shift 2
                ;;
            --skip-user)
                SKIP_USER_CREATION=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
RAG Configurator Demo Seeding Script

Usage: ./seed-demo.sh [options]

Options:
  --gateway-url URL    Gateway URL (default: http://localhost:8000)
  --skip-user          Skip user creation (use existing user)
  --help               Show this help message

Environment Variables:
  GATEWAY_URL          Gateway URL
  DEMO_USER_EMAIL      Demo user email (default: demo@techcorp.com)
  DEMO_USER_PASSWORD   Demo user password (default: DemoPass123!)
  DEMO_USER_NAME       Demo user name (default: Demo User)

Examples:
  ./seed-demo.sh                                    # Use defaults
  ./seed-demo.sh --gateway-url http://api.example.com  # Custom gateway
  ./seed-demo.sh --skip-user                        # Skip user creation
EOF
}

# Check if gateway is reachable
check_gateway() {
    log_info "Checking gateway at $GATEWAY_URL..."
    
    if ! curl -s "$GATEWAY_URL/health" > /dev/null 2>&1; then
        log_error "Gateway is not reachable at $GATEWAY_URL"
        log_info "Please ensure the gateway is running:"
        log_info "  make dev    # Start all services"
        log_info "  or"
        log_info "  docker-compose up -d"
        exit 1
    fi
    
    log_success "Gateway is reachable"
}

# Create demo user
create_user() {
    if [ "$SKIP_USER_CREATION" = true ]; then
        log_info "Skipping user creation (--skip-user flag set)"
        return 0
    fi
    
    log_info "Creating demo user: $DEMO_USER_EMAIL"
    
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$DEMO_USER_EMAIL\",
            \"password\": \"$DEMO_USER_PASSWORD\",
            \"name\": \"$DEMO_USER_NAME\"
        }" 2>/dev/null)
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 201 ] || [ "$http_code" -eq 200 ]; then
        log_success "Demo user created successfully"
    elif echo "$body" | grep -q "already exists" 2>/dev/null; then
        log_warning "User $DEMO_USER_EMAIL already exists"
    else
        log_error "Failed to create user (HTTP $http_code)"
        log_error "Response: $body"
        return 1
    fi
}

# Login and get token
login_user() {
    log_info "Logging in as $DEMO_USER_EMAIL..."
    
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$DEMO_USER_EMAIL\",
            \"password\": \"$DEMO_USER_PASSWORD\"
        }" 2>/dev/null)
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 200 ]; then
        ACCESS_TOKEN=$(echo "$body" | jq -r '.access_token')
        if [ "$ACCESS_TOKEN" != "null" ] && [ -n "$ACCESS_TOKEN" ]; then
            log_success "Login successful"
            export ACCESS_TOKEN
        else
            log_error "Failed to extract access token from response"
            log_error "Response: $body"
            return 1
        fi
    else
        log_error "Login failed (HTTP $http_code)"
        log_error "Response: $body"
        return 1
    fi
}

# Import a configuration
import_config() {
    local config_file="$1"
    local config_name="$2"
    
    if [ ! -f "$config_file" ]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi
    
    log_info "Importing configuration: $config_name"
    
    # Convert YAML to JSON (if needed) or send as-is
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/api/v1/configs/import" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -F "file=@$config_file" 2>/dev/null)
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 201 ] || [ "$http_code" -eq 200 ]; then
        local config_id
        config_id=$(echo "$body" | jq -r '.data.id // .data.config_id // .data._id // "unknown"')
        log_success "Configuration imported: $config_name (ID: $config_id)"
        
        # Store config ID for reference
        echo "$config_id" >> /tmp/imported_configs.txt
    else
        log_error "Failed to import $config_name (HTTP $http_code)"
        log_error "Response: $body"
        return 1
    fi
}

# Import all sample configurations
import_all_configs() {
    log_info "Importing sample configurations..."
    
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local configs_dir
    configs_dir="$(dirname "$script_dir")/sample-configs"
    
    if [ ! -d "$configs_dir" ]; then
        log_error "Sample configs directory not found: $configs_dir"
        return 1
    fi
    
    # Clear previous import tracking
    rm -f /tmp/imported_configs.txt
    
    # Import simple-rag
    if [ -f "$configs_dir/simple-flat.yaml" ]; then
        import_config "$configs_dir/simple-flat.yaml" "Simple Naive RAG" || log_warning "Skipping simple config import"
    fi
    
    # Skip other configs for now
    # # Import hybrid-rag
    # if [ -f "$configs_dir/hybrid-rag.yaml" ]; then
    #     import_config "$configs_dir/hybrid-rag.yaml" "Hybrid Multi-Query RAG"
    # fi
    
    # # Import graph-rag
    # if [ -f "$configs_dir/graph-rag.yaml" ]; then
    #     import_config "$configs_dir/graph-rag.yaml" "Graph ReAct RAG"
    # fi
    
    # # Import rbac-example
    # if [ -f "$configs_dir/rbac-example.yaml" ]; then
    #     import_config "$configs_dir/rbac-example.yaml" "RBAC Example"
    # fi
    
    log_success "All configurations imported"
    
    # Show summary
    if [ -f /tmp/imported_configs.txt ]; then
        local count
        count=$(wc -l < /tmp/imported_configs.txt)
        log_info "Total configurations imported: $count"
    fi
}

# Copy sample documents to ingestion folder
copy_sample_docs() {
    log_info "Setting up sample documents..."
    
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local docs_dir
    docs_dir="$(dirname "$script_dir")/sample-docs"
    local data_dir="${DATA_DIR:-./data}"
    
    if [ ! -d "$docs_dir" ]; then
        log_error "Sample docs directory not found: $docs_dir"
        return 1
    fi
    
    # Create data directories
    mkdir -p "$data_dir/documents"
    mkdir -p "$data_dir/technical-docs"
    mkdir -p "$data_dir/company-handbook"
    mkdir -p "$data_dir/research-papers"
    
    # Copy company handbook
    if [ -d "$docs_dir/company-handbook" ]; then
        cp -r "$docs_dir/company-handbook/"*.md "$data_dir/company-handbook/" 2>/dev/null || true
        log_success "Company handbook documents copied"
    fi
    
    # Copy technical docs
    if [ -d "$docs_dir/technical-docs" ]; then
        cp -r "$docs_dir/technical-docs/"*.md "$data_dir/technical-docs/" 2>/dev/null || true
        log_success "Technical documents copied"
    fi
    
    # Copy research papers
    if [ -d "$docs_dir/research-papers" ]; then
        cp -r "$docs_dir/research-papers/"*.md "$data_dir/research-papers/" 2>/dev/null || true
        log_success "Research papers copied"
    fi
    
    log_success "Sample documents set up in $data_dir"
    
    # Create a summary file
    cat > "$data_dir/README.txt" << EOF
RAG Configurator Demo Data
==========================

This directory contains sample documents for testing RAG configurations.

Folder Structure:
- company-handbook/    - HR policies, benefits, onboarding guides
- technical-docs/      - API guides, architecture docs, troubleshooting
- research-papers/     - Academic papers on RAG and vector search

Usage:
1. Configure a RAG pipeline to scan these directories
2. Run ingestion to process documents
3. Start querying!

For more information, see: https://docs.techcorp.com/demo
EOF
    
    log_info "Created README.txt in $data_dir"
}

# Test a query
test_query() {
    log_info "Testing query endpoint..."
    
    # Get first config ID
    local config_id
    if [ -f /tmp/imported_configs.txt ]; then
        config_id=$(head -n1 /tmp/imported_configs.txt)
    else
        log_warning "No configs found to test"
        return 0
    fi
    
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/api/v1/query" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -d "{
            \"config_id\": \"$config_id\",
            \"query\": \"What is RAG?\",
            \"options\": {
                \"stream\": false
            }
        }" 2>/dev/null)
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 202 ]; then
        log_success "Query endpoint test successful"
    else
        log_warning "Query endpoint test returned HTTP $http_code (this is OK if ingestion hasn't run)"
    fi
}

# Display summary
show_summary() {
    echo ""
    echo "========================================"
    echo -e "${GREEN}Demo Setup Complete!${NC}"
    echo "========================================"
    echo ""
    echo -e "${BLUE}Demo User:${NC}"
    echo "  Email:    $DEMO_USER_EMAIL"
    echo "  Password: $DEMO_USER_PASSWORD"
    echo ""
    echo -e "${BLUE}Access:${NC}"
    echo "  Gateway:  $GATEWAY_URL"
    echo "  Health:   $GATEWAY_URL/health"
    echo ""
    echo -e "${BLUE}Imported Configurations:${NC}"
    if [ -f /tmp/imported_configs.txt ]; then
        while IFS= read -r config_id; do
            echo "  - $config_id"
        done < /tmp/imported_configs.txt
    fi
    echo ""
    echo -e "${BLUE}Sample Documents:${NC}"
    local data_dir="${DATA_DIR:-./data}"
    echo "  Location: $data_dir"
    echo "  - company-handbook/ (policies, benefits, onboarding)"
    echo "  - technical-docs/ (API guides, architecture, troubleshooting)"
    echo "  - research-papers/ (RAG overview, vector search)"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Log in with the demo credentials"
    echo "  2. Select a configuration"
    echo "  3. Start a conversation or run ingestion"
    echo "  4. Ask questions about the documents!"
    echo ""
    echo -e "${BLUE}Example Queries:${NC}"
    echo "  - 'What are the remote work policies?'"
    echo "  - 'Explain the API authentication flow'"
    echo "  - 'How does HNSW algorithm work?'"
    echo ""
    echo "========================================"
}

# Main execution
main() {
    echo "========================================"
    echo "RAG Configurator Demo Setup"
    echo "========================================"
    echo ""
    
    # Parse arguments
    parse_args "$@"
    
    # Run setup steps
    check_dependencies
    check_gateway
    create_user
    login_user
    import_all_configs
    copy_sample_docs
    test_query
    
    # Show results
    show_summary
    
    # Cleanup
    rm -f /tmp/imported_configs.txt
    
    log_success "Demo seeding complete!"
}

# Run main function
main "$@"
