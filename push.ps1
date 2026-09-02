<#
  The Ember Loop - pubblicazione su GitHub

  Uso:
    powershell -ExecutionPolicy Bypass -File .\push.ps1 -Repo git@github.com:Anankayos/ember-loop.git

  Prima crea su github.com un repository VUOTO (senza README, senza .gitignore).
#>
param(
  [Parameter(Mandatory = $true)][string]$Repo,
  [string]$Branch = "main",
  [switch]$Force,
  [switch]$PuliziaStoria
)

# NIENTE ErrorActionPreference = Stop: git scrive normalmente su stderr
# (progresso, avvisi) e in PowerShell questo diventerebbe un errore terminante.
# Controlliamo invece $LASTEXITCODE dopo ogni chiamata.
$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Git {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs)
  $output = & git @GitArgs 2>&1 | ForEach-Object { "$_" }
  return [pscustomobject]@{ Ok = ($LASTEXITCODE -eq 0); Out = $output }
}
function Fail($msg) { Write-Host ""; Write-Host "  $msg" -ForegroundColor Red; Write-Host ""; exit 1 }

Write-Host ""
Write-Host "  THE EMBER LOOP - pubblicazione" -ForegroundColor DarkYellow
Write-Host "  cartella: $PSScriptRoot"
Write-Host ""

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Fail "git non e' installato. Scaricalo da https://git-scm.com/download/win"
}
if (-not (Test-Path ".gitignore")) {
  Fail ".gitignore MANCANTE. Mi fermo: senza di esso il foglio chiavi finirebbe online."
}

# ---- 1. repository ----
if (-not (Test-Path ".git")) {
  $r = Invoke-Git init -q;            if (-not $r.Ok) { Fail "git init fallito: $($r.Out)" }
  $r = Invoke-Git branch -M $Branch;  if (-not $r.Ok) { Fail "git branch fallito: $($r.Out)" }
  Write-Host "  [ok] repository inizializzato"
} else {
  Write-Host "  [..] repository gia' presente"
}

# ---- 1b. pulizia storia (ramo orfano: un solo commit, nessun passato) ----
if ($PuliziaStoria) {
  Write-Host ""
  Write-Host "  [!] PULIZIA STORIA: il repository remoto verra' riscritto con un solo commit." -ForegroundColor Yellow
  Write-Host "      I commit precedenti - e le chiavi che contenevano - spariscono dal ramo." -ForegroundColor Yellow
  $r = Invoke-Git checkout --orphan _pulito_tmp
  if (-not $r.Ok) { Fail "checkout orfano fallito: $($r.Out)" }
  Invoke-Git rm -r --cached . -q | Out-Null
  $Force = $true
  Write-Host "  [ok] ramo orfano creato"
}

# ---- 2. staging ----
$r = Invoke-Git add -A; if (-not $r.Ok) { Fail "git add fallito: $($r.Out)" }

$r = Invoke-Git diff --cached --name-only
if (-not $r.Ok) { Fail "impossibile leggere lo staging: $($r.Out)" }
$staged = @($r.Out | Where-Object { $_ -ne "" })

# ---- 3a. PROTEZIONE: file che non devono mai uscire ----
$vietati = @($staged | Where-Object { $_ -match 'CHIAVI-MASTER|contenuti\.py' })
if ($vietati.Count -gt 0) {
  Write-Host ""
  Write-Host "  FERMO TUTTO - file proibiti nello staging:" -ForegroundColor Red
  $vietati | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
  Invoke-Git reset -q | Out-Null
  Fail "Controlla .gitignore prima di riprovare."
}

# ---- 3b. PROTEZIONE: nessun segreto nel CONTENUTO di nessun file ----
# I segreti da cercare si leggono da CHIAVI-MASTER.md, che resta solo in locale.
$segreti = @()
if (Test-Path ".segreti") {
  $segreti = @(Get-Content ".segreti" | Where-Object { $_.Trim() -ne "" } | ForEach-Object { $_.Trim() })
}
if ($segreti.Count -eq 0) {
  Write-Host "  [!] .segreti non trovato: rigeneralo con  python contenuti.py" -ForegroundColor Yellow
} else {
  $trovati = @()
  foreach ($f in $staged) {
    if (-not (Test-Path $f)) { continue }
    $testo = Get-Content -Raw -ErrorAction SilentlyContinue $f
    if ($null -eq $testo) { continue }
    foreach ($sg in $segreti) {
      if ($testo -cmatch [regex]::Escape($sg)) { $trovati += ("{0}  contiene  {1}" -f $f, $sg) }
    }
  }
  if ($trovati.Count -gt 0) {
    Write-Host ""
    Write-Host "  FERMO TUTTO - segreti trovati DENTRO questi file:" -ForegroundColor Red
    $trovati | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    Invoke-Git reset -q | Out-Null
    Fail "Togli il segreto dal file, oppure aggiungi il file a .gitignore."
  }
  Write-Host ("  [ok] nessun segreto, ne' come nome file ne' come contenuto ({0} verificati)" -f $segreti.Count)
}

# ---- 4. commit ----
# 'git rev-parse --verify HEAD' e' il modo corretto di sapere se ci sono commit:
# in un repo vuoto esce con codice != 0 invece di stampare un errore fatale.
Invoke-Git rev-parse --verify HEAD | Out-Null
$primoCommit = ($LASTEXITCODE -ne 0)

if ($staged.Count -gt 0) {
  Write-Host ""
  Write-Host "  File che verranno pubblicati ($($staged.Count)):" -ForegroundColor DarkCyan
  $staged | ForEach-Object { Write-Host "    $_" }
  Write-Host ""
  $msg = if ($primoCommit) { "The Ember Loop - software di sessione" } else { "Aggiornamento contenuti" }
  $r = Invoke-Git commit -q -m $msg
  if (-not $r.Ok) { Fail "git commit fallito: $($r.Out)`n  Se dice 'Please tell me who you are', imposta:`n    git config --global user.name  ""Alessandro Pesetti""`n    git config --global user.email ""alessandro.pesetti@gmail.com""" }
  Write-Host "  [ok] commit creato"
  if ($PuliziaStoria) {
    $r = Invoke-Git branch -M $Branch
    if (-not $r.Ok) { Fail "impossibile rinominare il ramo: $($r.Out)" }
    Write-Host "  [ok] ramo orfano promosso a '$Branch' - storia precedente eliminata"
  }
} else {
  if ($primoCommit) { Fail "Non c'e' niente da committare e nessun commit esistente." }
  Write-Host "  [..] nessuna modifica da committare"
}

# ---- 5. remote ----
$r = Invoke-Git remote
$haOrigin = @($r.Out) -contains 'origin'
$r = if ($haOrigin) { Invoke-Git remote set-url origin $Repo } else { Invoke-Git remote add origin $Repo }
if (-not $r.Ok) { Fail "impossibile impostare origin: $($r.Out)" }
Write-Host "  [ok] origin -> $Repo"

# ---- 6. push ----
Write-Host ""
Write-Host "  Push in corso..." -ForegroundColor DarkYellow
$argsPush = @("push","-u","origin",$Branch)
if ($Force) { $argsPush += "--force"; Write-Host "  [!] push forzato: sovrascrive il contenuto remoto" -ForegroundColor Yellow }
$r = Invoke-Git @argsPush
$r.Out | ForEach-Object { Write-Host "    $_" -ForegroundColor Yellow }
$r.Out | Out-File -Encoding utf8 (Join-Path $PSScriptRoot "push-log.txt")

if (-not $r.Ok) {
  Write-Host ""
  Write-Host "  Il push e' fallito. Cause tipiche:" -ForegroundColor Red
  Write-Host "    - il repo su github.com non esiste ancora: creane uno VUOTO"
  Write-Host "    - il repo non e' vuoto (ha gia' un README): allora usa"
  Write-Host "        git push -u origin $Branch --force"
  Write-Host "    - con URL ssh la chiave non e' caricata. Prova:  ssh -T git@github.com"
  Write-Host "    - con URL https serve un Personal Access Token al posto della password"
  exit 1
}

$slug = $Repo -replace '.*[:/]([^/]+/[^/]+?)(\.git)?$', '$1'
$parti = $slug -split '/'
$utente = $parti[0]; $nome = $parti[1]

Write-Host ""
Write-Host "  FATTO." -ForegroundColor Green
Write-Host ""
Write-Host "  Ultimo passo, a mano su GitHub:"
Write-Host "    Settings -> Pages -> Source: '$Branch' / (root) -> Save"
Write-Host ""
Write-Host "  Dopo un paio di minuti:"
Write-Host "    https://$utente.github.io/$nome/             app dei tre ruoli + console" -ForegroundColor Cyan
Write-Host "    https://$utente.github.io/$nome/stampa.html  materiali da stampare" -ForegroundColor Cyan
Write-Host ""
Write-Host "  CHIAVI-MASTER.md resta solo sul tuo disco. Stampalo." -ForegroundColor DarkYellow
Write-Host ""
