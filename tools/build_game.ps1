param([string]$Name = 'ArrowOrder')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$gamePython = Join-Path $projectRoot '.venv\Scripts\python.exe'
Push-Location $projectRoot
try {
    & $gamePython -m PyInstaller --noconfirm --onefile --windowed `
        --name $Name --workpath build/game --specpath build --distpath dist `
        --add-data "${projectRoot}/assets/fonts/ArrowOrder-Regular.ttf:assets/fonts" `
        --add-data "${projectRoot}/assets/fonts/ArrowOrder-Semibold.ttf:assets/fonts" `
        --add-data "${projectRoot}/assets/fonts/OFL.txt:assets/fonts" `
        --add-data "${projectRoot}/assets/audio/quiet_afternoon.wav:assets/audio" `
        --add-data "${projectRoot}/assets/images/fail_cat.jpg:assets/images" `
        --add-data "${projectRoot}/assets/images/last_chance_cat.jpg:assets/images" `
        --add-data "${projectRoot}/assets/images/three_star_cat.jpg:assets/images" `
        --add-data "${projectRoot}/assets/images/github_mark.png:assets/images" `
        --add-data "${projectRoot}/assets/cg:assets/cg" game.py
    if ($LASTEXITCODE -ne 0) { throw 'Game build failed.' }
    Copy-Item -LiteralPath 'README.md' -Destination 'dist/GAME_README.md' -Force
    Copy-Item -LiteralPath 'assets/fonts/OFL.txt' -Destination 'dist/OFL.txt' -Force
    Write-Host "EXE created: dist/$Name.exe"
} finally { Pop-Location }
