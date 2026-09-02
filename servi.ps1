<#
  Serve la cartella in rete locale, per provare le app dal telefono.
  Uso:  tasto destro su questo file -> "Esegui con PowerShell"
        oppure:  powershell -ExecutionPolicy Bypass -File .\servi.ps1

  NOTA: da telefono funziona tutto TRANNE la scansione QR.
  I browser permettono la fotocamera solo in contesto sicuro (https,
  oppure localhost). Un indirizzo http://192.168.x.x non lo e'.
  Per provare anche la fotocamera serve GitHub Pages, che e' https.
#>
param([int]$Porta = 8000)

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
$esclusi = @()
if (Test-Path ".gitignore") {
  $esclusi = @(Get-Content ".gitignore" | ForEach-Object { $_.Trim() } |
               Where-Object { $_ -and -not $_.StartsWith("#") } |
               ForEach-Object { $_.TrimEnd("/") })
}
$esclusi += @("servi.ps1", "push.ps1", "_serve")

$dest = Join-Path $PSScriptRoot "_serve"
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
New-Item -ItemType Directory -Path $dest | Out-Null

$copiati = @(); $tenuti = @()
foreach ($f in Get-ChildItem -File -Force) {
  if ($esclusi -contains $f.Name) { $tenuti += $f.Name; continue }
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
Write-Host "  Dal telefono, sulla stessa rete Wi-Fi, apri:" -ForegroundColor Cyan
Write-Host ""
Write-Host "      http://${ip}:${Porta}/prova-offline.html" -ForegroundColor Green
Write-Host ""
Write-Host "  Dal PC:  http://localhost:${Porta}/prova-offline.html"
Write-Host "  (su localhost la fotocamera funziona: e' considerato sicuro)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Materiali da stampare:  http://${ip}:${Porta}/stampa.html"
Write-Host ""
Write-Host "  Se Windows chiede di autorizzare Python nel firewall, di' SI" -ForegroundColor Yellow
Write-Host "  e spunta 'Reti private'. Senza, il telefono non vede il PC." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Servo solo $($copiati.Count) file pubblici." -ForegroundColor DarkGray
Write-Host "  Restano fuori dalla rete: $($tenuti -join ', ')" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Ctrl+C per fermare il server." -ForegroundColor DarkGray
Write-Host ""

& $py -m http.server $Porta --bind 0.0.0.0
