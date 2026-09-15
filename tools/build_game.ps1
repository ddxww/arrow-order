$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$gamePython = Join-Path $projectRoot '.venv\Scripts\python.exe'
Push-Location $projectRoot
try {
    & $gamePython -m PyInstaller --noconfirm --onefile --windowed `
        --name ArrowOrder --workpath build/game --specpath build --distpath dist `
        --add-data "${projectRoot}/assets/fonts/ArrowOrder-Regular.ttf:assets/fonts" `
        --add-data "${projectRoot}/assets/fonts/ArrowOrder-Semibold.ttf:assets/fonts" `
        --add-data "${projectRoot}/assets/fonts/OFL.txt:assets/fonts" game.py
    if ($LASTEXITCODE -ne 0) { throw 'Game build failed.' }
    Copy-Item -LiteralPath 'README.md' -Destination 'dist/GAME_README.md' -Force
    Copy-Item -LiteralPath 'assets/fonts/OFL.txt' -Destination 'dist/OFL.txt' -Force
    Write-Host 'EXE created: dist/ArrowOrder.exe'
} finally { Pop-Location }
