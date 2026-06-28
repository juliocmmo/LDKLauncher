# build.ps1 — Script de build do LDKLauncher
# Uso: .\build.ps1  (com o venv ativo)
#
# Pré-requisitos:
#   pip install pyinstaller
#   Inno Setup 6 instalado em C:\Program Files (x86)\Inno Setup 6\

$ErrorActionPreference = "Stop"
$VERSAO = "1.3.0"
$ISCC = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

Write-Host "=== LDKLauncher Build v$VERSAO ===" -ForegroundColor Cyan

# Passo 1 — Verificar pré-requisitos
Write-Host "`n[0/4] Verificando pré-requisitos..." -ForegroundColor Yellow
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "pyinstaller não encontrado. Execute: pip install pyinstaller"
}
if (-not (Test-Path $ISCC)) {
    throw "Inno Setup não encontrado em '$ISCC'. Instale em https://jrsoftware.org/isinfo.php"
}
if (-not (Test-Path "launcher\core\credentials.py")) {
    throw "launcher\core\credentials.py não encontrado. Gere com gen_credentials.py antes de buildar."
}

# Passo 2 — Limpar builds anteriores
Write-Host "`n[1/4] Limpando builds anteriores..." -ForegroundColor Yellow
if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "LDKLauncher.zip") { Remove-Item -Force "LDKLauncher.zip" }

# Passo 3 — PyInstaller
Write-Host "`n[2/4] Gerando executável com PyInstaller..." -ForegroundColor Yellow
pyinstaller LDKLauncher.spec --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou. Verifique os erros acima." }

# Passo 4 — Inno Setup
Write-Host "`n[3/4] Gerando instalador com Inno Setup..." -ForegroundColor Yellow
& $ISCC "installer\LDKLauncher.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falhou. Verifique os erros acima." }

# Passo 5 — Zip para o auto-updater
Write-Host "`n[4/4] Criando LDKLauncher.zip para o auto-updater..." -ForegroundColor Yellow
Compress-Archive -Path "dist\LDKLauncher\*" -DestinationPath "LDKLauncher.zip" -Force

Write-Host "`n=== Build concluído! ===" -ForegroundColor Green
Write-Host "  Instalador:   LDKLauncher-Setup.exe  (para novos usuários)"
Write-Host "  Auto-updater: LDKLauncher.zip         (para atualizações automáticas)"
Write-Host ""
Write-Host "Publicar no GitHub:" -ForegroundColor Cyan
Write-Host "  gh release create v$VERSAO LDKLauncher-Setup.exe LDKLauncher.zip --title ""v$VERSAO"""
