param(
    [int]$Port = 8000,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

Write-Host "[API] Revisando puerto $Port..."
$lines = netstat -ano | Select-String ":$Port"
$pids = @()

foreach ($line in $lines) {
    $parts = ($line.ToString() -replace "\s+", " ").Trim().Split(" ")
    if ($parts.Length -ge 5 -and $parts[1] -like "*:$Port" -and $parts[3] -eq "LISTENING") {
        $pidValue = [int]$parts[4]
        if ($pidValue -gt 0 -and $pids -notcontains $pidValue) {
            $pids += $pidValue
        }
    }
}

foreach ($pidValue in $pids) {
    try {
        $proc = Get-Process -Id $pidValue -ErrorAction Stop
        Write-Host "[API] Cerrando proceso en puerto ${Port}: PID=$pidValue Nombre=$($proc.ProcessName)"
        Stop-Process -Id $pidValue -Force
    } catch {
        Write-Host "[API] No se pudo cerrar PID=$pidValue. Continuando..."
    }
}

Write-Host "[API] Iniciando servidor en http://127.0.0.1:${Port}"
Start-Process -FilePath "python" -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port $Port --reload" -WorkingDirectory $PSScriptRoot

Start-Sleep -Seconds 2

if ($OpenBrowser) {
    Start-Process "http://127.0.0.1:${Port}/"
    Start-Process "http://127.0.0.1:${Port}/docs"
}

Write-Host "[API] Listo. Si no abre automáticamente, navega a http://127.0.0.1:${Port}/"
