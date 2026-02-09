# RAG Configurator - Ingestion & RAG Testing Script (PowerShell)
# This script helps you verify ingestion and test RAG functionality

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$ConfigId,

    [Parameter(Position=1)]
    [string]$TestQuery = "What is this document about?"
)

$GATEWAY_URL = "http://localhost:8000"
$ErrorActionPreference = "Continue"

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Blue
Write-Host "║   RAG Configurator - Ingestion & RAG Testing Script       ║" -ForegroundColor Blue
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Blue
Write-Host ""
Write-Host "Testing with config_id: $ConfigId" -ForegroundColor Yellow
Write-Host ""

function Print-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
    Write-Host "  $Title" -ForegroundColor Blue
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
    Write-Host ""
}

# 1. Check Ingestion Status
Print-Header "1. Checking Ingestion Status"
Write-Host "Querying: GET $GATEWAY_URL/api/v1/ingest/$ConfigId/status"
try {
    $StatusResponse = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/ingest/$ConfigId/status" -Method Get
    $StatusResponse | ConvertTo-Json -Depth 10 | Write-Host

    Write-Host ""
    Write-Host "Status Summary:" -ForegroundColor Green
    Write-Host "  Status: $($StatusResponse.status)"
    Write-Host "  Progress: $($StatusResponse.progress)%"
    Write-Host "  Files: $($StatusResponse.processed_files)/$($StatusResponse.total_files) processed, $($StatusResponse.failed_files) failed"
    Write-Host "  Total Chunks: $($StatusResponse.total_chunks)"

    if ($StatusResponse.status -eq "none") {
        Write-Host ""
        Write-Host "⚠ No ingestion has been started for this config." -ForegroundColor Yellow
        Write-Host "Start ingestion from the UI at http://localhost:5173"
        exit 0
    }
    elseif ($StatusResponse.status -eq "pending" -or $StatusResponse.status -eq "running") {
        Write-Host ""
        Write-Host "⏳ Ingestion is still in progress. Please wait..." -ForegroundColor Yellow
        Write-Host "You can monitor progress in real-time by running this script again."
    }
    elseif ($StatusResponse.status -eq "completed") {
        Write-Host ""
        Write-Host "✓ Ingestion completed successfully!" -ForegroundColor Green
    }
    elseif ($StatusResponse.status -eq "failed") {
        Write-Host ""
        Write-Host "✗ Ingestion failed. Check logs for details." -ForegroundColor Red
    }

    $Status = $StatusResponse.status
    $TotalChunks = $StatusResponse.total_chunks
}
catch {
    Write-Host "Error checking status: $_" -ForegroundColor Red
    exit 1
}

# 2. Get Detailed Statistics
Print-Header "2. Ingestion Statistics"
Write-Host "Querying: GET $GATEWAY_URL/api/v1/ingest/$ConfigId/stats"
try {
    $StatsResponse = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/ingest/$ConfigId/stats" -Method Get
    $StatsResponse | ConvertTo-Json -Depth 10 | Write-Host
}
catch {
    Write-Host "Error getting stats: $_" -ForegroundColor Red
}

# 3. Check Ingestion Logs
Print-Header "3. Recent Ingestion Logs"
Write-Host "Querying: GET $GATEWAY_URL/api/v1/ingest/$ConfigId/logs?limit=5"
try {
    $LogsResponse = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/ingest/$ConfigId/logs?limit=5" -Method Get
    $LogsResponse.logs | ConvertTo-Json -Depth 10 | Write-Host
}
catch {
    Write-Host "Error getting logs: $_" -ForegroundColor Red
}

# 4. Verify Data in MongoDB
Print-Header "4. Data Verification"
Write-Host "To verify ingested data in MongoDB:" -ForegroundColor Yellow
Write-Host "  1. Open MongoDB Express: http://localhost:8081"
Write-Host "  2. Navigate to 'rag_configurator' database"
Write-Host "  3. Check these collections:"
Write-Host "     • 'documents' - Raw document metadata"
Write-Host "     • 'chunks' - Chunked text with embeddings"
Write-Host "     • 'ingestions' - Ingestion history and status"
if ($TotalChunks -gt 0) {
    Write-Host ""
    Write-Host "✓ Found $TotalChunks chunks in the database" -ForegroundColor Green
}

# 5. Test RAG Query (only if ingestion completed)
if ($Status -eq "completed" -and $TotalChunks -gt 0) {
    Print-Header "5. Testing RAG Query"

    Write-Host "Test Query: `"$TestQuery`"" -ForegroundColor Yellow
    Write-Host "Querying: POST $GATEWAY_URL/api/v1/query/"

    $QueryPayload = @{
        query = $TestQuery
        config_id = $ConfigId
        include_sources = $true
        include_debug = $true
    } | ConvertTo-Json

    Write-Host ""
    Write-Host "Request payload:"
    Write-Host $QueryPayload
    Write-Host ""

    try {
        $QueryResponse = Invoke-RestMethod -Uri "$GATEWAY_URL/api/v1/query/" `
            -Method Post `
            -ContentType "application/json" `
            -Body $QueryPayload

        Write-Host "✓ RAG Query Successful!" -ForegroundColor Green
        Write-Host ""

        Write-Host "Answer:" -ForegroundColor Green
        Write-Host $QueryResponse.answer
        Write-Host ""

        Write-Host "Metadata:" -ForegroundColor Green
        Write-Host "  Agent Type: $($QueryResponse.metadata.agent_type)"
        Write-Host "  Duration: $($QueryResponse.metadata.total_duration_ms)ms"
        Write-Host "  Sources: $($QueryResponse.sources.Count) chunks"
        Write-Host ""

        if ($QueryResponse.sources.Count -gt 0) {
            Write-Host "Source Chunks:" -ForegroundColor Green
            foreach ($source in $QueryResponse.sources) {
                $preview = $source.content.Substring(0, [Math]::Min(100, $source.content.Length))
                Write-Host "  • [$($source.source_type)] Score: $($source.score) - $preview..."
            }
        }

        if ($QueryResponse.debug) {
            Write-Host ""
            Write-Host "Debug Information:" -ForegroundColor Green
            $QueryResponse.debug | ConvertTo-Json -Depth 10 | Write-Host
        }
    }
    catch {
        Write-Host "✗ RAG Query Failed" -ForegroundColor Red
        Write-Host "Error: $_"
    }

    # 6. Access Sandbox UI
    Print-Header "6. Interactive Testing"
    Write-Host "For interactive testing, use the Sandbox UI:" -ForegroundColor Yellow
    Write-Host "  URL: http://localhost:3001"
    Write-Host ""
    Write-Host "In the Sandbox UI, you can:"
    Write-Host "  • Enter your config_id: $ConfigId"
    Write-Host "  • Chat with your documents interactively"
    Write-Host "  • See real-time responses with source citations"
    Write-Host "  • Test different queries"
}
else {
    Print-Header "5. RAG Testing"
    Write-Host "⚠ Cannot test RAG query yet" -ForegroundColor Yellow
    if ($Status -ne "completed") {
        Write-Host "Reason: Ingestion status is '$Status' (need 'completed')"
    }
    elseif ($TotalChunks -eq 0) {
        Write-Host "Reason: No chunks found in database"
    }
    Write-Host ""
    Write-Host "Wait for ingestion to complete, then run this script again."
}

# Summary
Print-Header "Summary"
Write-Host "Available Resources:" -ForegroundColor Green
Write-Host "  • Configurator UI: http://localhost:5173"
Write-Host "  • Sandbox UI: http://localhost:3001"
Write-Host "  • MongoDB Express: http://localhost:8081"
Write-Host "  • Redis Commander: http://localhost:8082"
Write-Host "  • Gateway API: http://localhost:8000"
Write-Host ""
Write-Host "Useful PowerShell Commands:" -ForegroundColor Yellow
Write-Host "  # Check status"
Write-Host "  Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/ingest/$ConfigId/status' | ConvertTo-Json"
Write-Host ""
Write-Host "  # Get stats"
Write-Host "  Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/ingest/$ConfigId/stats' | ConvertTo-Json"
Write-Host ""
Write-Host "  # Test query"
Write-Host "  `$body = @{query='Your question?'; config_id='$ConfigId'} | ConvertTo-Json"
Write-Host "  Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query/' -Method Post -ContentType 'application/json' -Body `$body"
Write-Host ""
Write-Host "Testing complete!" -ForegroundColor Green
