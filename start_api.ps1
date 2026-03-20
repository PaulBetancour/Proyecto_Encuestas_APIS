param(
    [int]$Port = 8000,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

Write-Host "[API] Revisando puerto $Port..."
$pythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    throw "No se encontro el entorno virtual en $pythonPath"
}

$candidatePorts = @($Port, 8001, 8010) | Select-Object -Unique
$selectedPort = $null

foreach ($candidatePort in $candidatePorts) {
    Write-Host "[API] Revisando puerto $candidatePort..."
    $lines = netstat -ano | Select-String ":$candidatePort"
    $pids = @()

    foreach ($line in $lines) {
        $parts = ($line.ToString() -replace "\s+", " ").Trim().Split(" ")
        if ($parts.Length -ge 5 -and $parts[1] -like "*:$candidatePort" -and $parts[3] -eq "LISTENING") {
            $pidValue = [int]$parts[4]
            if ($pidValue -gt 0 -and $pids -notcontains $pidValue) {
                $pids += $pidValue
            }
        }
    }

    foreach ($pidValue in $pids) {
        try {
            $proc = Get-Process -Id $pidValue -ErrorAction Stop
            Write-Host "[API] Cerrando proceso en puerto ${candidatePort}: PID=$pidValue Nombre=$($proc.ProcessName)"
            Stop-Process -Id $pidValue -Force
        } catch {
            Write-Host "[API] No se pudo cerrar PID=$pidValue. Continuando..."
        }
    }

    Write-Host "[API] Iniciando servidor en http://127.0.0.1:${candidatePort}"
    Start-Process -FilePath $pythonPath -ArgumentList "-m","uvicorn","main:app","--host","127.0.0.1","--port",$candidatePort -WorkingDirectory $PSScriptRoot | Out-Null

    Start-Sleep -Seconds 4

    try {
        $response = Invoke-WebRequest "http://127.0.0.1:${candidatePort}/docs" -UseBasicParsing -TimeoutSec 10
        Write-Host "[API] OK -> /docs responde con status $($response.StatusCode)"
        $selectedPort = $candidatePort
        break
    } catch {
        Write-Host "[API] El puerto ${candidatePort} no respondio correctamente. Probando otro puerto..."
    }
}

if ($null -eq $selectedPort) {
    throw "La API no pudo iniciar correctamente en ninguno de los puertos: $($candidatePorts -join ', ')"
}

if ($OpenBrowser) {
    Start-Process "http://127.0.0.1:${selectedPort}/"
    Start-Process "http://127.0.0.1:${selectedPort}/docs"
    Start-Process "http://127.0.0.1:${selectedPort}/redoc"
}

Write-Host "[API] Listo. Si no abre automáticamente, navega a http://127.0.0.1:${selectedPort}/"
