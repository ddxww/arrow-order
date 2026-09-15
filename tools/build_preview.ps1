$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previewPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
Push-Location $projectRoot
try {
    & $previewPython -m PyInstaller --noconfirm --onefile --windowed `
        --name ArrowOrder-Preview --workpath build/preview --specpath build --distpath dist `
        --add-data "${projectRoot}/assets/fonts/ArrowOrder-Regular.ttf:assets/fonts" `
        --add-data "${projectRoot}/assets/fonts/ArrowOrder-Semibold.ttf:assets/fonts" `
        --add-data "${projectRoot}/assets/fonts/OFL.txt:assets/fonts" preview.py
    if ($LASTEXITCODE -ne 0) { throw 'Preview build failed.' }
    Copy-Item -LiteralPath 'docs/PREVIEW_DELIVERY.md' -Destination 'dist/README.md' -Force
    Copy-Item -LiteralPath 'assets/fonts/OFL.txt' -Destination 'dist/OFL.txt' -Force
    Compress-Archive -LiteralPath 'dist/ArrowOrder-Preview.exe','dist/README.md','dist/OFL.txt' `
        -DestinationPath 'dist/ArrowOrder-Preview-Windows.zip' -Force
    Write-Host 'EXE created: dist/ArrowOrder-Preview.exe'
} finally {
    Pop-Location
}
