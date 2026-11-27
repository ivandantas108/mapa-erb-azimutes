$RootDir = $PSScriptRoot
Set-Location $RootDir

function Write-Secao($texto) {
    Write-Host ""
    Write-Host "==== $texto ====" -ForegroundColor Cyan
}

Write-Secao "Encerrando a aplicacao e o link publico"

$pidFile = Join-Path $RootDir ".publicar_app_pids.json"
$algoParado = $false

if (Test-Path $pidFile) {
    try {
        $pids = Get-Content $pidFile | ConvertFrom-Json

        if ($pids.streamlit) {
            $p = Get-Process -Id $pids.streamlit -ErrorAction SilentlyContinue
            if ($p) {
                Stop-Process -Id $pids.streamlit -Force -ErrorAction SilentlyContinue
                Write-Host "Aplicacao (Streamlit) encerrada." -ForegroundColor Green
                $algoParado = $true
            }
        }

        if ($pids.tunnel) {
            $p = Get-Process -Id $pids.tunnel -ErrorAction SilentlyContinue
            if ($p) {
                Stop-Process -Id $pids.tunnel -Force -ErrorAction SilentlyContinue
                Write-Host "Tunel publico (cloudflared) encerrado." -ForegroundColor Green
                $algoParado = $true
            }
        }
    } catch {
        Write-Host "Nao foi possivel ler o arquivo de controle ($pidFile)." -ForegroundColor Yellow
    }

    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# Garantia extra: mata qualquer cloudflared/streamlit deste projeto que ainda esteja
# escutando na porta padrao, mesmo se o arquivo de controle estiver ausente/desatualizado.
try {
    Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue |
        ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            $algoParado = $true
        }
} catch {}

if ($algoParado) {
    Write-Host ""
    Write-Host "Tudo encerrado. O link publico nao funciona mais." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Nada estava rodando (ja estava parado)." -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Pressione Enter para fechar esta janela"
