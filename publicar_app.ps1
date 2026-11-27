param(
    [int]$Porta = 8501
)

$ErrorActionPreference = "Stop"
$RootDir = $PSScriptRoot
Set-Location $RootDir

function Write-Secao($texto) {
    Write-Host ""
    Write-Host "==== $texto ====" -ForegroundColor Cyan
}

function Sair-ComErro($mensagem) {
    Write-Host "ERRO: $mensagem" -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit 1
}

# ---------------------------------------------------------------------------
# 1. Python
# ---------------------------------------------------------------------------
Write-Secao "Verificando Python"
try {
    $pyVersion = & python --version 2>&1
    Write-Host "OK: $pyVersion"
} catch {
    Sair-ComErro "Python nao encontrado no PATH. Instale em https://www.python.org/downloads/ (marque a opcao 'Add python.exe to PATH' durante a instalacao) e rode este arquivo de novo."
}

# ---------------------------------------------------------------------------
# 2. Ambiente virtual + dependencias
# ---------------------------------------------------------------------------
$venvPath = Join-Path $RootDir "venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvStreamlit = Join-Path $venvPath "Scripts\streamlit.exe"

if (-not (Test-Path $venvPython)) {
    Write-Secao "Criando ambiente virtual (venv) - so acontece na primeira vez nesta maquina"
    & python -m venv $venvPath
    if (-not (Test-Path $venvPython)) {
        Sair-ComErro "Nao foi possivel criar o ambiente virtual."
    }
}

Write-Secao "Instalando dependencias (pode levar alguns minutos na primeira vez)"
& $venvPython -m pip install --quiet --disable-pip-version-check -r (Join-Path $RootDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Sair-ComErro "Falha ao instalar dependencias do requirements.txt."
}

# ---------------------------------------------------------------------------
# 3. Login (gera credenciais padrao se esta maquina nunca rodou o app antes)
# ---------------------------------------------------------------------------
$secretsDir = Join-Path $RootDir ".streamlit"
$secretsFile = Join-Path $secretsDir "secrets.toml"

if (-not (Test-Path $secretsFile)) {
    Write-Secao "Gerando configuracao de login padrao (primeira vez nesta maquina)"
    New-Item -ItemType Directory -Force -Path $secretsDir | Out-Null

    $tmpGerador = Join-Path $RootDir "_gerar_secrets_tmp.py"
    @"
import secrets
import streamlit_authenticator as stauth

senha_hash = stauth.Hasher.hash("admin")
cookie_key = secrets.token_hex(32)

conteudo = f'''[credentials]
[credentials.usernames.admin]
name = "Administrador"
password = "{senha_hash}"

[cookie]
name = "mapa_erb_auth"
key = "{cookie_key}"
expiry_days = 30
'''

with open(r"$secretsFile", "w", encoding="utf-8") as f:
    f.write(conteudo)
"@ | Set-Content -Path $tmpGerador -Encoding utf8

    & $venvPython $tmpGerador
    Remove-Item $tmpGerador -Force

    Write-Host "Login padrao criado: usuario 'admin', senha 'admin'." -ForegroundColor Yellow
    Write-Host "Para trocar a senha depois: venv\Scripts\python gerar_hash_senha.py" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 4. cloudflared (cria o link publico)
# ---------------------------------------------------------------------------
Write-Secao "Verificando cloudflared"
$cloudflaredCmd = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflaredCmd) {
    Write-Host "cloudflared nao encontrado. Tentando instalar via winget..."
    try {
        winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
    } catch {
        Write-Host "winget falhou ou nao esta disponivel." -ForegroundColor Yellow
    }
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $cloudflaredCmd = Get-Command cloudflared -ErrorAction SilentlyContinue
}
if (-not $cloudflaredCmd) {
    Sair-ComErro "Nao foi possivel instalar o cloudflared automaticamente. Baixe manualmente em https://github.com/cloudflare/cloudflared/releases/latest (arquivo cloudflared-windows-amd64.exe), renomeie para cloudflared.exe e coloque nesta mesma pasta do projeto. Depois rode este arquivo de novo."
}

# ---------------------------------------------------------------------------
# 5. Encerrar qualquer instancia anterior desta mesma aplicacao
# ---------------------------------------------------------------------------
Write-Secao "Liberando a porta $Porta, se necessario"
try {
    Get-NetTCPConnection -LocalPort $Porta -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
} catch {}

$pidFile = Join-Path $RootDir ".publicar_app_pids.json"
if (Test-Path $pidFile) {
    try {
        $pids_antigos = Get-Content $pidFile | ConvertFrom-Json
        foreach ($p in @($pids_antigos.streamlit, $pids_antigos.tunnel)) {
            if ($p) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
        }
    } catch {}
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

# ---------------------------------------------------------------------------
# 6. Iniciar a aplicacao (Streamlit)
# ---------------------------------------------------------------------------
Write-Secao "Iniciando a aplicacao"
$streamlitLog = Join-Path $RootDir "streamlit.log"
$streamlitErrLog = Join-Path $RootDir "streamlit.err.log"
$streamlitProc = Start-Process -FilePath $venvStreamlit `
    -ArgumentList "run app.py --server.headless true --server.port $Porta" `
    -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $streamlitLog -RedirectStandardError $streamlitErrLog

Write-Host "Aguardando a aplicacao responder..."
$ok = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:$Porta" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $ok = $true; break }
    } catch {}
}
if (-not $ok) {
    Sair-ComErro "A aplicacao nao respondeu a tempo. Veja os logs em: $streamlitLog e $streamlitErrLog"
}
Write-Host "Aplicacao no ar em http://localhost:$Porta" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 7. Abrir o tunel publico (Cloudflare)
# ---------------------------------------------------------------------------
Write-Secao "Criando o link publico"
$tunnelLog = Join-Path $RootDir "tunnel.log"
$tunnelErrLog = Join-Path $RootDir "tunnel.err.log"
if (Test-Path $tunnelLog) { Remove-Item $tunnelLog -Force }
if (Test-Path $tunnelErrLog) { Remove-Item $tunnelErrLog -Force }

$tunnelProc = Start-Process -FilePath "cloudflared" `
    -ArgumentList "tunnel --url http://localhost:$Porta" `
    -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $tunnelLog -RedirectStandardError $tunnelErrLog

$publicUrl = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    foreach ($arquivoLog in @($tunnelErrLog, $tunnelLog)) {
        if (Test-Path $arquivoLog) {
            $match = Select-String -Path $arquivoLog -Pattern "https://[a-zA-Z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($match) {
                $publicUrl = $match.Matches[0].Value
                break
            }
        }
    }
    if ($publicUrl) { break }
}

if (-not $publicUrl) {
    Stop-Process -Id $streamlitProc.Id -Force -ErrorAction SilentlyContinue
    Sair-ComErro "Nao foi possivel obter o link publico. Veja os logs em: $tunnelLog e $tunnelErrLog"
}

@{ streamlit = $streamlitProc.Id; tunnel = $tunnelProc.Id } | ConvertTo-Json | Set-Content -Path $pidFile

try { Set-Clipboard -Value $publicUrl } catch {}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  LINK PUBLICO (acessivel de qualquer computador/rede):"           -ForegroundColor Green
Write-Host "  $publicUrl"                                                     -ForegroundColor White
Write-Host "  (ja copiado para a area de transferencia)"                      -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Login: usuario 'admin', senha 'admin' (a menos que ja tenha trocado)" -ForegroundColor Yellow
Write-Host ""
Write-Host "IMPORTANTE:" -ForegroundColor Cyan
Write-Host " - A aplicacao e o tunel rodam em segundo plano: pode fechar esta"
Write-Host "   janela, o link continua no ar."
Write-Host " - O computador nao pode suspender/hibernar nem perder internet."
Write-Host " - Cada vez que voce rodar este arquivo, o link muda (e um novo tunel)."
Write-Host " - Para ENCERRAR de vez, rode parar_app.bat."
Write-Host ""

Read-Host "Pressione Enter para fechar esta janela"
