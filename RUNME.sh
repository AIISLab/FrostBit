#!/usr/bin/env bash
set -e

echo "=== Backend: Python environment and dependencies ==="
echo "=== Checking system dependencies (Python 3.11+, Node.js/npm) ==="

# ---------- Python install (macOS/Linux) ----------
if ! command -v python3.11 &>/dev/null; then
  echo "Python 3.11 is not installed."

  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Installing Python 3.11 via Homebrew..."
    if ! command -v brew &>/dev/null; then
      echo "Homebrew not found. Installing Homebrew..."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    brew install python@3.11
  else
    echo "Attempting Python 3.11 installation via apt..."
    if command -v apt &>/dev/null; then
      sudo apt update
      sudo apt install -y python3.11 python3.11-venv python3.11-distutils
    else
      echo "ERROR: Could not auto-install Python 3.11 (non-apt Linux). Please install manually."
      exit 1
    fi
  fi
else
  echo "Python 3.11 already installed."
fi

# ---------- Node.js/npm install ----------
if ! command -v npm &>/dev/null; then
  echo "npm not found; installing Node.js..."

  if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &>/dev/null; then
      echo "Installing Homebrew first..."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    brew install node
  else
    if command -v apt &>/dev/null; then
      curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
      sudo apt install -y nodejs
    else
      echo "ERROR: npm not installed and cannot auto-install on this platform."
      exit 1
    fi
  fi
else
  echo "Node.js/npm already installed."
fi

# 1) Pick a Python executable (prefer 3.11)
if command -v python3.11 &>/dev/null; then
  PY=python3.11
elif command -v python3 &>/dev/null; then
  PY=python3
elif command -v python &>/dev/null; then
  PY=python
else
  echo "ERROR: Python 3.11+ is not installed or not in PATH."
  exit 1
fi

# 2) Check Python version
PY_VERSION="$($PY -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
PY_MAJOR="$($PY -c 'import sys; print(sys.version_info[0])')"
PY_MINOR="$($PY -c 'import sys; print(sys.version_info[1])')"

echo "Using Python executable: $PY (version $PY_VERSION)"

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
  echo "ERROR: This project requires Python 3.11 or newer (numpy==2.3.5)."
  echo "Current version is $PY_VERSION. Please install Python 3.11 and re-run RUNME.sh."
  exit 1
fi

# 3) Create venv if missing
if [ ! -d ".venv" ]; then
  $PY -m venv .venv
fi

# 4) Activate venv
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo "ERROR: Could not activate virtual environment."
  exit 1
fi

# 5) Install Python deps (adjust path if your requirements live elsewhere)
if [ -f "server/requirements.txt" ]; then
  REQ_FILE="server/requirements.txt"
elif [ -f "requirements.txt" ]; then
  REQ_FILE="requirements.txt"
else
  echo "ERROR: Could not find requirements.txt or server/requirements.txt."
  exit 1
fi

echo "Installing Python dependencies from $REQ_FILE ..."
pip install --upgrade pip
pip install -r "$REQ_FILE"

echo
echo "=== Frontend: Node/npm dependencies ==="

# 6) Check npm
if ! command -v npm &>/dev/null; then
  echo "ERROR: npm is not installed or not in PATH."
  exit 1
fi

# 7) Detect frontend directory
FRONTEND_DIR="."
if [ -f "web/package.json" ]; then
  FRONTEND_DIR="web"
fi

echo "Using frontend directory: $FRONTEND_DIR"

cd "$FRONTEND_DIR"
npm install
cd ..

echo
echo "=== All set! ==="
echo "To run the backend:"
echo "  source .venv/bin/activate"
echo "  uvicorn main:app --reload --port 8000"
echo
echo "To run the frontend:"
if [ "$FRONTEND_DIR" != "." ]; then
  echo "  cd $FRONTEND_DIR"
fi
echo "  npm run dev"
