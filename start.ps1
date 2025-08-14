# Load variables from .env file
Get-Content ".env" | ForEach-Object {
    if ($_ -match "^\s*#") { return }
    if ($_ -match "^\s*$") { return }
    $name, $value = $_ -split "=", 2
    $value = $value.Trim('"') # remove quotes if any
    Set-Item -Path Env:$name -Value $value
}

# Confirm variables loaded
Write-Host "Loaded environment variables:"
Write-Host "AZURE_OPENAI_ENDPOINT=$env:AZURE_OPENAI_ENDPOINT"
Write-Host "AZURE_OPENAI_DEPLOYMENT=$env:AZURE_OPENAI_DEPLOYMENT"
Write-Host "AZURE_OPENAI_API_VERSION=$env:AZURE_OPENAI_API_VERSION"

# Start uvicorn
uvicorn main:app --reload
