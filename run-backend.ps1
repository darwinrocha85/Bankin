# Corre el backend de BankIn en local.
#
# Uso normal (doble click o desde PowerShell):
#   .\run-backend.ps1
#
# Con datos de prueba (puebla la base si está vacía):
#   .\run-backend.ps1 -Seed
#
# Si Windows se queja de que la ejecución de scripts está deshabilitada,
# corre esto una vez en esa terminal y vuelve a intentar:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

param(
    [switch]$Seed
)

# Permite que ESTE script (y la activación del venv) corran en esta sesión,
# sin tocar la política de ejecución global de Windows.
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# Se ubica siempre en la carpeta donde vive este script (la raíz del
# backend), sin importar desde dónde lo hayas ejecutado.
Set-Location $PSScriptRoot

if (-not (Test-Path ".\venv")) {
    Write-Host "No existe el entorno virtual, creándolo e instalando dependencias..." -ForegroundColor Yellow
    python -m venv venv
    & .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
} else {
    & .\venv\Scripts\Activate.ps1
}

if ($Seed) {
    Write-Host "AUTO_SEED activado: si la base está vacía, se poblará con datos de prueba al arrancar." -ForegroundColor Cyan
    $env:AUTO_SEED = "true"
}

Write-Host ""
Write-Host "Backend disponible en  http://localhost:8000" -ForegroundColor Green
Write-Host "Docs interactivas en   http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Health check en        http://localhost:8000/health" -ForegroundColor Green
Write-Host ""
Write-Host "(Ctrl+C para detenerlo)" -ForegroundColor DarkGray
Write-Host ""

python -m uvicorn app.main:app --reload
