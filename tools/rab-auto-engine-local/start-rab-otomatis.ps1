$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$bundledPython = "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$python = "python"
try {
  & $python -c "import tempfile" | Out-Null
} catch {
  if (Test-Path $bundledPython) {
    $python = $bundledPython
  }
}
& $python -m pip install -r requirements.txt
& $python -m uvicorn backend.app:app --host 127.0.0.1 --port 8787 --reload
