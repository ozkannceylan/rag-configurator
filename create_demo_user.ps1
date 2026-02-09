# Create Demo User for RAG Configurator

$body = @{
    email = "demo@techcorp.com"
    password = "DemoPass123!"
    name = "Demo User"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/register" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body `
        -ErrorAction Stop

    Write-Host "✓ Demo user created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Login credentials:" -ForegroundColor Cyan
    Write-Host "  Email: demo@techcorp.com"
    Write-Host "  Password: DemoPass123!"
    Write-Host ""
    if ($response.access_token) {
        Write-Host "Access Token: $($response.access_token.Substring(0,20))..."
    }
} catch {
    $errorMessage = $_.ToString()
    if ($errorMessage -match "409" -or $errorMessage -match "already exists") {
        Write-Host "✓ Demo user already exists!" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Login credentials:" -ForegroundColor Cyan
        Write-Host "  Email: demo@techcorp.com"
        Write-Host "  Password: DemoPass123!"
    } else {
        Write-Host "Error creating user: $errorMessage" -ForegroundColor Red
    }
}
