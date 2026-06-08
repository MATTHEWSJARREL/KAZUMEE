param(
  [string]$PythonPath = ".\\venv311\\Scripts\\python"
)

Write-Host "Running migrations..." -ForegroundColor Cyan
& $PythonPath -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Seeding demo data..." -ForegroundColor Cyan
& $PythonPath backend\\seed_db.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "DB setup complete." -ForegroundColor Green
