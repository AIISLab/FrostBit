# ❄️ FrostBit — Project Overview

FrostBit is an early-season frost risk decision-support system designed for specialty crop growers. It brings together:

CIMIS weather data (hourly air temperature, relative humidity, dew point, wind, etc.)

Physiological frost-damage models for almond phenological stages

A FastAPI backend that normalizes, caches, and computes frost-risk indices

A React/Vite frontend for interactive visualization

The system ingests hourly CIMIS observations, computes wet‑bulb and blossom temperatures, estimates cooling rates, and applies stage-specific frost damage curves to output a GeoJSON Feature containing frost risk, lethal temperature thresholds (LT10/LT90), and environmental drivers.

This API is meant to be consumed directly by the frontend using lightweight fetch() calls, providing a consistent structure regardless of crop or station.

# ❄️ FrostBit — Quickstart Guide

FrostBit is a full-stack project consisting of:

- **FastAPI backend** (Python 3.11+ required)
- **React/Vite frontend**
- **Automation scripts** to install dependencies and launch both services with minimal effort

This README provides the *fastest possible setup path* for reviewers and developers.

---

## 📌 Requirements

### Backend
- **Python 3.11+**  
  (_Required — numpy 2.3+ does **not** support earlier Python versions_)

### Frontend
- **Node.js 18+**
- **npm**

### Optional Tools
- macOS/Linux shell  
- Windows PowerShell  

---

# 🚀 Quickstart

## 1. Clone the repository

```bash
git clone https://github.com/AIISLab/FrostBit
cd FrostBit
```


---

# 📦 2. Automatic Dependency Installation

You can install everything (backend + frontend) with a single script.

---

### macOS / Linux

```bash
chmod +x RUNME.sh
./RUNME.sh
```

---

### Windows (PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\RUNME.ps1
```

These scripts:

- Create a Python virtual environment  
- Install backend dependencies (`server/requirements.txt`)  
- Install frontend dependencies (`web/package.json`)  

---

# ▶️ 3. Launch the Application (Recommended)

Run **both** backend and frontend automatically.

---

### macOS / Linux

```bash
chmod +x LAUNCH_ALL.sh
./LAUNCH_ALL.sh
```

---

### Windows (PowerShell)

```powershell
.\LAUNCH_ALL.ps1
```

This starts:

| Component | URL                   |
|----------|-----------------------|
| **Backend API** | http://localhost:8000 |
| **Frontend (Vite Dev Server)** | http://localhost:3000 |

Both processes remain running until you press `CTRL + C`.

---

# 🛠️ 4. Manual Start (Optional)

If you prefer launching components individually:

---

### Backend (FastAPI)

```bash
cd server
source ../.venv/bin/activate          # macOS/Linux
# OR
.\.venv\Scripts\Activate.ps1          # Windows PowerShell

uvicorn app.main:app --reload --port 8000
```

---

### Frontend (React/Vite)

```bash
cd web
npm run dev
```

Open the frontend at:

👉 http://localhost:3000

Open interactive API docs (Swagger):

👉 http://localhost:8000/docs

---

# 📁 Project Structure

```
FrostBit/
├── server/               # FastAPI backend
│   ├── app/main.py
│   └── requirements.txt
├── web/                  # React/Vite frontend
│   └── package.json
├── RUNME.sh              # macOS/Linux automated installer
├── RUNME.ps1             # Windows automated installer
├── LAUNCH_ALL.sh         # macOS/Linux client+server launcher
├── LAUNCH_ALL.ps1        # Windows client+server launcher
└── README.md
```

---

# 🧪 Verifying Everything Works

After launching:

### Frontend  
👉 http://localhost:3000

### Backend API Docs  
👉 http://localhost:8000/docs

You should see a working Vite app + Swagger UI.

---

# ❓ Troubleshooting

### ❗ Python version error  
This project **requires Python 3.11+**.  
If macOS default Python is older, install 3.11 via:

```bash
brew install python@3.11
```

### ❗ npm not found  
Install Node.js from:

https://nodejs.org/

### ❗ Port already in use  
Edit:

- `uvicorn … --port 8000` in launcher scripts  
- Vite config (or run `npm run dev -- --port 5174`)

---

# 🙋 Need More?

I can generate:

- Dockerized build  
- Production deployment instructions  
- One-click unified installer  
- A prettier README with badges, logos, and screenshots  
- Automated tests or CI pipeline  

Just ask!
