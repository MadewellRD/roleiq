#requires -Version 7.0

param(
    [switch] $SkipDependencyInstall
)

$ErrorActionPreference = "Stop"

$Repo = $PSScriptRoot
$Venv = Join-Path $Repo ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$Activate = Join-Path $Venv "Scripts\Activate.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "             RoleIQ V1.92" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------
# Repository
# ------------------------------------------------------------

if (-not (Test-Path $Repo)) {
    throw "RoleIQ repository not found: $Repo"
}

Set-Location $Repo

Write-Host "[1/6] Repository: $Repo" -ForegroundColor Green

if (-not (Test-Path ".\app.py")) {
    throw "app.py was not found in $Repo"
}

if (-not (Test-Path ".\requirements.txt")) {
    throw "requirements.txt was not found in $Repo"
}

# ------------------------------------------------------------
# Python
# ------------------------------------------------------------

Write-Host "[2/6] Checking Python..." -ForegroundColor Green

try {
    $PythonVersion = & python --version 2>&1
}
catch {
    throw "Python was not found. Install Python 3.11 or 3.12 and ensure it is on PATH."
}

Write-Host "       $PythonVersion"

if ($PythonVersion -match "Python (\d+)\.(\d+)") {
    $Major = [int]$Matches[1]
    $Minor = [int]$Matches[2]
    if ($Major -ne 3 -or $Minor -lt 11) {
        Write-Host "       WARNING: RoleIQ is validated on Python 3.11+; found $PythonVersion. Continuing." -ForegroundColor Yellow
    }
}

# ------------------------------------------------------------
# Virtual environment
# ------------------------------------------------------------

Write-Host "[3/6] Checking virtual environment..." -ForegroundColor Green

if (-not (Test-Path $Python)) {
    Write-Host "       Creating .venv..." -ForegroundColor Yellow

    & python -m venv $Venv

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Python virtual environment."
    }
}
else {
    Write-Host "       Existing .venv found."
}

# ------------------------------------------------------------
# Activate
# ------------------------------------------------------------

if (-not (Test-Path $Activate)) {
    throw "Virtual environment activation script not found: $Activate"
}

$CurrentPolicy = Get-ExecutionPolicy -Scope Process
if ($CurrentPolicy -in @("Restricted", "AllSigned", "Default")) {
    Write-Host "       Process execution policy is $CurrentPolicy; allowing script execution for this process only." -ForegroundColor Yellow
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
}
else {
    Write-Host "       Process execution policy is $CurrentPolicy; no bypass needed." -ForegroundColor DarkGray
}
& $Activate

# ------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------

if ($SkipDependencyInstall) {
    Write-Host "[4/6] Skipping dependency install (-SkipDependencyInstall)." -ForegroundColor DarkGray
}
else {
    Write-Host "[4/6] Installing/updating dependencies..." -ForegroundColor Green

    & $Python -m pip install --upgrade pip

    if ($LASTEXITCODE -ne 0) {
        throw "pip upgrade failed."
    }

    & $Python -m pip install -r ".\requirements.txt"

    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }
}

# ------------------------------------------------------------
# Application validation
# ------------------------------------------------------------

Write-Host "[5/6] Validating RoleIQ..." -ForegroundColor Green

& $Python -m py_compile ".\app.py" ".\ai_provider.py" ".\check_providers.py" ".\db_crypto.py" ".\role_schema.py"

if ($LASTEXITCODE -ne 0) {
    throw "Python compilation failed. RoleIQ was not started."
}

Write-Host "       Source compilation: PASS" -ForegroundColor Green

# ------------------------------------------------------------
# API key
# ------------------------------------------------------------

Write-Host "[6/6] Checking AI provider configuration..." -ForegroundColor Green

function Read-ApiKeyIntoEnv {
    param(
        [Parameter(Mandatory = $true)][string] $Prompt,
        [Parameter(Mandatory = $true)][string] $EnvName
    )

    $SecureKey = Read-Host $Prompt -AsSecureString

    $BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)

    try {
        $Plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($BSTR)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
    }

    if ([string]::IsNullOrWhiteSpace($Plain)) {
        Write-Host "No key entered." -ForegroundColor Yellow
        return
    }

    Set-Item -Path "Env:$EnvName" -Value $Plain
    Write-Host "$EnvName configured for this session." -ForegroundColor Green
    $Plain = $null  # best-effort: drop the reference so GC can reclaim it; .NET strings can't be forcibly zeroed
}

$HasAnthropic = -not [string]::IsNullOrWhiteSpace($env:ANTHROPIC_API_KEY)
$HasOpenAI = -not [string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)

if (-not $HasAnthropic -and -not $HasOpenAI) {

    Write-Host ""
    Write-Host "No AI provider key is currently configured." -ForegroundColor Yellow
    Write-Host "RoleIQ uses one provider per run. Anthropic wins if both keys are set." -ForegroundColor DarkGray
    Write-Host ""

    $Choice = Read-Host "Configure a key now? (A)nthropic / (O)penAI / (N)o"

    switch -Regex ($Choice) {
        "^[Aa]" { Read-ApiKeyIntoEnv -Prompt "Anthropic API key" -EnvName "ANTHROPIC_API_KEY" }
        "^[Oo]" { Read-ApiKeyIntoEnv -Prompt "OpenAI API key" -EnvName "OPENAI_API_KEY" }
        default {
            Write-Host "Continuing without an API key. AI functionality will not work until one is configured." -ForegroundColor Yellow
        }
    }

    $HasAnthropic = -not [string]::IsNullOrWhiteSpace($env:ANTHROPIC_API_KEY)
    $HasOpenAI = -not [string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)
}

if ($HasAnthropic) {
    Write-Host "       ANTHROPIC_API_KEY: configured" -ForegroundColor Green
}

if ($HasOpenAI) {
    Write-Host "       OPENAI_API_KEY: configured" -ForegroundColor Green
}

if ($HasAnthropic) {
    Write-Host "       Active provider: Anthropic (Claude)" -ForegroundColor Cyan

    if ($HasOpenAI) {
        Write-Host "       Both keys present - Anthropic takes precedence for text." -ForegroundColor DarkGray
    }
}
elseif ($HasOpenAI) {
    Write-Host "       Active provider: OpenAI" -ForegroundColor Cyan
}

if ($HasOpenAI) {
    Write-Host "       Voice transcription: available (OpenAI)" -ForegroundColor DarkGray
}
else {
    Write-Host "       Voice transcription: unavailable - needs OPENAI_API_KEY" -ForegroundColor DarkGray
}

# ------------------------------------------------------------
# Launch
# ------------------------------------------------------------

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting RoleIQ..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "URL: http://localhost:8501" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop RoleIQ." -ForegroundColor DarkGray
Write-Host ""

& $Python -m streamlit run ".\app.py"