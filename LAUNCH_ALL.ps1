# SERVER window
Start-Process powershell -ArgumentList "
    cd server;
    ..\.venv\Scripts\Activate.ps1;
    uvicorn app.main:app --reload --port 8000
"

# CLIENT window
Start-Process powershell -ArgumentList "
    cd web;
    npm run dev
"

Write-Host "Launched client + server in separate windows."
