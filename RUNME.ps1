Write-Host "=== Backend: Python environment and dependencies ==="
Write-Host "=== Checking system dependencies (Python 3.11+, Node.js/npm) ==="

# ---------- Python check/install ----------
$py = Get-Command python3.11 -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python 3.11 not found."

    Write-Host "Attempting installation via winget..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install Python.Python.3.11 --source winget --disable-interactivity
    } else {
        Write-Host "ERROR: winget not available. Install Python 3.11 manually from python.org."
        exit 1
    }
} else {
    Write-Host "Python 3.11 already installed."
}

# ---------- Node.js/npm check/install ----------
$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    Write-Host "npm not found. Installing Node.js via winget..."

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install OpenJS.NodeJS.LTS --source winget --disable-interactivity
    } else {
        Write-Host "ERROR: winget not available. Install Node.js manually from nodejs.org."
        exit 1
    }
} else {
    Write-Host "Node.js/npm already installed."
}

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Create venv if missing
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

# Activate venv
$venvActivate = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "Activating virtual environment..."
    & $venvActivate
} else {
    Write-Host "ERROR: venv activation script not found." -ForegroundColor Red
    exit 1
}

# Install Python deps
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "`n=== Frontend: Node/npm dependencies ==="

# Check npm
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: npm is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Detect frontend directory
$frontendDir = "."
if (Test-Path "web/package.json") {
    $frontendDir = "web"
}

Write-Host "Using frontend directory: $frontendDir"

# Install Node deps
Set-Location $frontendDir
npm install
Set-Location ..

Write-Host "`n=== All set! ===" -ForegroundColor Green
Write-Host ""
Write-Host "To run the backend:"
Write-Host "  1) .\.venv\Scripts\Activate.ps1"
Write-Host "  2) uvicorn main:app --reload --port 8000"
Write-Host ""
Write-Host "To run the frontend:"
if ($frontendDir -ne ".") {
    Write-Host "  cd $frontendDir"
}
Write-Host "  npm run dev"
Write-Host ""
Write-Host "Done!"
