param(
  [string]$InputMd = "docs/master_log/Master_Log.md",
  [string]$Css = "docs/master_log/pdf.css"
)

# build_master_log.ps1 — Markdown -> PDF using md-to-pdf (Node)
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/build_master_log.ps1
#   powershell -ExecutionPolicy Bypass -File scripts/build_master_log.ps1 -InputMd "docs/master_log/Master_Log.md"

$ErrorActionPreference = "Stop"

if (!(Test-Path $InputMd)) { throw "Missing input markdown: $InputMd" }
if (!(Test-Path $Css))     { throw "Missing stylesheet: $Css" }

# Prefer npx so md-to-pdf can be installed per-repo as a devDependency:
#   npm i -D md-to-pdf
# Or install globally:
#   npm i -g md-to-pdf
if (!(Get-Command npx -ErrorAction SilentlyContinue)) {
  Write-Error "npx not found. Install Node.js (includes npm/npx), then run: npm i -D md-to-pdf"
  exit 1
}

# md-to-pdf writes the PDF next to the .md file with the same base name.
# Run from the directory containing the markdown file so paths resolve correctly.
$Dir = Split-Path -Parent $InputMd
$File = Split-Path -Leaf $InputMd
$CssAbs = (Resolve-Path $Css).Path

Push-Location $Dir
try {
  & npx --yes md-to-pdf $File --stylesheet $CssAbs 2>&1 | Out-Null
} catch {
  & npx md-to-pdf $File --stylesheet $CssAbs 2>&1 | Out-Null
}
Pop-Location

$Output = [System.IO.Path]::ChangeExtension($InputMd, ".pdf")
Write-Host "Built $Output"
