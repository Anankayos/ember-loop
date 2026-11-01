<#
  Serve la cartella in rete locale, per provare le app dal telefono.
  Uso:  tasto destro su questo file -> "Esegui con PowerShell"
        oppure:  powershell -ExecutionPolicy Bypass -File .\servi.ps1

  In http la scansione QR NON parte: i browser danno la fotocamera solo
  in contesto sicuro (https, oppure localhost), e http://192.168.x.x non lo e'.
  Si digita il codice stampato sotto il sigillo, e funziona tutto il resto.

  Per riavere lo scanner:  .\servi.ps1 -Https
  Fa un certificato per l'IP di questo PC e serve in https. Sul telefono, la
  prima volta, Chrome mette un avviso: Avanzate -> Procedi. Da li' in poi la
  fotocamera parte. (GitHub Pages non si puo' piu' usare: i testi in chiaro
  sono dentro dati.js, quindi il repository non puo' restare pubblico.)
#>
param([int]$Porta = 8000, [switch]$Https)

$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot

# --- trova python ---
$py = $null
foreach ($c in @('python','py','python3')) {
  if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
  Write-Host ""
  Write-Host "  Python non trovato." -ForegroundColor Red
  Write-Host "  Installalo da https://www.python.org/downloads/  (spunta 'Add to PATH')"
  Write-Host ""
  exit 1
}

# --- indirizzo in rete locale ---
$ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
       Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and
                      $_.PrefixOrigin -in @('Dhcp','Manual') } |
       Sort-Object -Property @{Expression={ if ($_.InterfaceAlias -match 'Wi-Fi|Wireless') {0} else {1} }} |
       Select-Object -First 1).IPAddress
if (-not $ip) { $ip = '127.0.0.1' }

# --- costruisce una cartella con i SOLI file pubblici -------------------
# python -m http.server espone tutto cio' che trova. Se servissimo la cartella
# di progetto, chiunque sulla stessa Wi-Fi - cioe' i tuoi giocatori - potrebbe
# aprire CHIAVI-MASTER.md dal telefono. Quindi serviamo solo una copia filtrata.
# Lista BIANCA, non nera: esce solo quello che il browser deve scaricare davvero.
# Una lista nera si e' gia' dimostrata fragile - i caratteri jolly di .gitignore non
# venivano applicati e Materials*.xlsx finiva sulla Wi-Fi - e un file binario la
# scansione dei segreti qui sotto non lo sa nemmeno leggere.
$ammesse = @('.html', '.js', '.css', '.json', '.png', '.jpg', '.jpeg', '.svg', '.ico', '.webmanifest')
$esclusi = @("servi.ps1", "push.ps1", "_serve")
if (Test-Path ".gitignore") {
  $esclusi += @(Get-Content ".gitignore" | ForEach-Object { $_.Trim() } |
                Where-Object { $_ -and -not $_.StartsWith("#") } |
                ForEach-Object { $_.TrimEnd("/") })
}

$dest = Join-Path $PSScriptRoot "_serve"
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
New-Item -ItemType Directory -Path $dest | Out-Null

$copiati = @(); $tenuti = @()
foreach ($f in Get-ChildItem -File -Force) {
  $fuori = $false
  if ($ammesse -notcontains $f.Extension.ToLower()) { $fuori = $true }
  foreach ($e in $esclusi) {
    if ($e -match '[*?]') { if ($f.Name -like $e) { $fuori = $true } }
    elseif ($f.Name -eq $e) { $fuori = $true }
  }
  if ($fuori) { $tenuti += $f.Name; continue }
  Copy-Item $f.FullName -Destination $dest
  $copiati += $f.Name
}

# controllo finale: nessun segreto deve essere finito nella copia servita
if (Test-Path ".segreti") {
  $segreti = @(Get-Content ".segreti" | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() })
  $perdite = @()
  foreach ($f in Get-ChildItem -Path $dest -File) {
    $txt = Get-Content -Raw -ErrorAction SilentlyContinue $f.FullName
    if ($null -eq $txt) { continue }
    foreach ($sg in $segreti) { if ($txt -cmatch [regex]::Escape($sg)) { $perdite += "$($f.Name) contiene $sg" } }
  }
  if ($perdite.Count -gt 0) {
    Write-Host ""
    Write-Host "  NON AVVIO IL SERVER - segreti nei file da servire:" -ForegroundColor Red
    $perdite | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    Remove-Item $dest -Recurse -Force
    exit 1
  }
}
Set-Location -LiteralPath $dest

Write-Host ""
Write-Host "  THE EMBER LOOP - server di prova" -ForegroundColor DarkYellow
Write-Host ""
$schema = if ($Https) { 'https' } else { 'http' }
$url = "${schema}://${ip}:${Porta}/prova-offline.html"

Write-Host "  Dal telefono, sulla stessa rete Wi-Fi, apri:" -ForegroundColor Cyan
Write-Host ""
Write-Host "      $url" -ForegroundColor Green
Write-Host ""

# --- il QR per entrare senza digitare l'indirizzo ---
# I telefoni lo inquadrano con la fotocamera normale: Android apre Chrome da solo.
$qr = Join-Path $PSScriptRoot "qr_terminale.py"
if (Test-Path $qr) {
  $prima = [Console]::OutputEncoding
  try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    & $py $qr $url
    if ($LASTEXITCODE -ne 0) {
      Write-Host "  (niente QR: manca il modulo qrcode -> pip install qrcode)" -ForegroundColor DarkGray
    }
  } finally { [Console]::OutputEncoding = $prima }
  Write-Host ""
}

if ($Https) {
  Write-Host "  La prima volta Chrome mette un avviso sul certificato:" -ForegroundColor Yellow
  Write-Host "  Avanzate -> Procedi. Serve una volta sola per telefono." -ForegroundColor Yellow
  Write-Host "  Da li' in poi lo scanner QR funziona." -ForegroundColor Yellow
} else {
  Write-Host "  In http lo scanner QR non parte: si digita il codice sotto il sigillo." -ForegroundColor DarkGray
  Write-Host "  Per riavere lo scanner:  .\servi.ps1 -Https" -ForegroundColor DarkGray
}
Write-Host ""
Write-Host "  Dal PC:  ${schema}://localhost:${Porta}/prova-offline.html"
Write-Host "  (su localhost la fotocamera funziona comunque: e' considerato sicuro)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Materiali da stampare:  ${schema}://${ip}:${Porta}/stampa.html"
Write-Host ""
Write-Host "  Se Windows chiede di autorizzare Python nel firewall, di' SI" -ForegroundColor Yellow
Write-Host "  e spunta 'Reti private'. Senza, il telefono non vede il PC." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Servo solo $($copiati.Count) file pubblici." -ForegroundColor DarkGray
Write-Host "  Restano fuori dalla rete: $($tenuti -join ', ')" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Ctrl+C per fermare il server." -ForegroundColor DarkGray
Write-Host ""

if ($Https) {
  $tls = Join-Path $PSScriptRoot "servi_tls.py"
  if (-not (Test-Path $tls)) {
    Write-Host "  manca servi_tls.py: servo in http." -ForegroundColor Red
    & $py -m http.server $Porta --bind 0.0.0.0
  } else {
    & $py $tls $Porta (Join-Path $PSScriptRoot ".cert") $ip
  }
} else {
  & $py -m http.server $Porta --bind 0.0.0.0
}
