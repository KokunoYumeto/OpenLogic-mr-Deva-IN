[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'build'),
    [ValidateRange(1,10000)][int]$AcquireTimeoutMs = 1500,
    [ValidateRange(60000,900000)][int]$PassTimeoutMs = 480000,
    [switch]$Cumulative
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$jobname = 'slc-screen'
$inputFile = if ($Cumulative) { 'slc-screen-mr.tex' } else { 'slc-screen.tex' }
$python = (Get-Command python -CommandType Application | Select-Object -First 1).Source
$outDir = [IO.Path]::GetFullPath($OutputDirectory)
$null = New-Item -ItemType Directory -Path $outDir -Force
$runName = 'screen-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfff') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$stage = Join-Path $outDir $runName
$null = New-Item -ItemType Directory -Path $stage
$receiptPath = Join-Path $stage 'BUILD.json'
$receipt = [ordered]@{ schema='openlogic-slc-marathi-build/1'; status='staging';
    input=$inputFile; source_date_epoch='1783832456'; mutex='Global\InterlanguageTeXSlotV1';
    acquired=$false; released=$false; abandoned_recovery=$false; commands=@() }
$receipt.source_root = $root
$sourceManifest = Join-Path $root 'MANIFEST.json'
if (Test-Path -LiteralPath $sourceManifest -PathType Leaf) {
    $receipt.source_manifest_sha256 = (Get-FileHash -LiteralPath $sourceManifest).Hash.ToLowerInvariant()
}
$envBefore = @{}
foreach ($name in 'SOURCE_DATE_EPOCH','FORCE_SOURCE_DATE','BSTINPUTS','TZ') {
    $envBefore[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$mutex = $null
$portableLock = $null
$held = $false
$insideStage = $false

function Run-SlcTool([string]$Tool, [string[]]$Arguments) {
    $exe = (Get-Command $Tool -CommandType Application | Select-Object -First 1).Source
    $console = Join-Path $stage ('{0:D2}-{1}.txt' -f ($receipt.commands.Count + 1), $Tool)
    $entry = [ordered]@{ tool=$Tool; arguments=$Arguments; exit_code=$null }
    $receipt.commands += $entry
    if ($IsWindows) {
        # Fixed arguments below contain only ASCII switches and stage-relative file names.
        $entry.exit_code = [SlcTexTree]::Run($exe, ($Arguments -join ' '), $stage, $console, $PassTimeoutMs)
    } else {
        & $exe @Arguments *> $console
        $entry.exit_code = $LASTEXITCODE
    }
    if (Test-Path -LiteralPath $console) {
        $entry.console = Split-Path -Leaf $console
        $entry.console_sha256 = (Get-FileHash -LiteralPath $console).Hash.ToLowerInvariant()
    }
    $diagnostic = switch ($Tool) { 'xelatex' { '.log' } 'bibtex' { '.blg' } 'makeindex' { '.glg' } }
    $path = Join-Path $stage ($jobname + $diagnostic)
    if (Test-Path -LiteralPath $path) {
        $entry.log_sha256 = (Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()
    }
    if ($entry.exit_code -ne 0) {
        if (Test-Path -LiteralPath $path) { Get-Content -LiteralPath $path -Encoding utf8 -Tail 30 | Write-Host }
        elseif (Test-Path -LiteralPath $console) { Get-Content -LiteralPath $console -Encoding utf8 -Tail 30 | Write-Host }
        throw "$Tool returned $($entry.exit_code). See $stage."
    }
}

try {
    & $python -X utf8 (Join-Path $root 'prepare_build.py') $root $stage $inputFile
    if ($LASTEXITCODE -ne 0) { throw 'Exact source staging failed.' }
    $receipt.input_sha256 = (Get-FileHash -LiteralPath (Join-Path $stage $inputFile)).Hash.ToLowerInvariant()
    $receipt.inputs_sha256 = (Get-FileHash -LiteralPath (Join-Path $stage 'INPUTS.json')).Hash.ToLowerInvariant()
    if ($IsWindows) {
        if (-not ('SlcTexTree' -as [type])) { Add-Type -Path (Join-Path $root 'WindowsTeXTree.cs') }
        $mutex = [Threading.Mutex]::new($false, 'Global\InterlanguageTeXSlotV1')
        try { $held = $mutex.WaitOne($AcquireTimeoutMs) }
        catch [Threading.AbandonedMutexException] { $held=$true; $receipt.abandoned_recovery=$true }
    } else {
        # Separate local fallback for readers building outside the Windows host.
        $receipt.mutex = 'local-temporary-file-lock'
        $lockfile = Join-Path ([IO.Path]::GetTempPath()) 'interlanguage-tex-slot-v1.lock'
        try { $portableLock = [IO.File]::Open($lockfile, 'OpenOrCreate', 'ReadWrite', 'None'); $held = $true }
        catch [IO.IOException] { $held = $false }
    }
    $receipt.acquired = $held
    if (-not $held) {
        $receipt.status = 'slot_occupied'
        throw 'The shared TeX slot is occupied. No compiler was started.'
    }
    Push-Location -LiteralPath $stage
    $insideStage = $true
    $env:SOURCE_DATE_EPOCH = $receipt.source_date_epoch
    $env:FORCE_SOURCE_DATE = '1'
    $env:TZ = 'UTC'
    $env:BSTINPUTS = (Join-Path $stage 'open-logic/bib') + [IO.Path]::PathSeparator
    $receipt.engine = (& xelatex --version | Select-Object -First 1)
    $receipt.bibtex = (& bibtex --version | Select-Object -First 1)
    $miktexArgs = if ($receipt.engine -match 'MiKTeX') { @('--disable-installer') } else { @() }
    $texArgs = @($miktexArgs) + @('-no-shell-escape','-interaction=nonstopmode','-halt-on-error',
        '-file-line-error','-recorder','-synctex=1',"-jobname=$jobname",'slc-screen.tex')
    $bibArgs = @($miktexArgs) + @($jobname)
    $indexArgs = @('-s',"$jobname.ist",'-t',"$jobname.glg",'-o',"$jobname.gls","$jobname.glo")
    $checks = @('There were undefined (?:references|citations)',
        '(?:Reference|Citation) [^\r\n]{0,200} undefined', 'Label\(s\) may have changed',
        'Rerun to get (?:cross-references|outlines) right', 'multiply defined',
        'Token [^\r\n]{0,200} undefined', 'requested but not marked mr',
        'Missing character:', 'Photo credits .* not found', 'No file .*\.(?:bbl|gls)\.',
        'destination with the same identifier')
    $logFile = Join-Path $stage "$jobname.log"
    Run-SlcTool xelatex $texArgs
    $firstLog = Get-Content -LiteralPath $logFile -Raw -Encoding utf8
    if (($firstLog -replace '\s+', ' ') -match 'requested but not marked mr') { throw 'Unmarked Marathi import.' }
    Run-SlcTool bibtex $bibArgs
    Run-SlcTool makeindex $indexArgs
    $warnings = @()
    for ($pass = 2; $pass -le 7; $pass++) {
        $auxPath = Join-Path $stage "$jobname.aux"
        $before = Get-Content -LiteralPath $auxPath -Encoding utf8 | Where-Object { $_ -match '^\\(?:citation|bibdata|bibstyle)\{' } | Sort-Object -Unique
        Run-SlcTool xelatex $texArgs
        $after = Get-Content -LiteralPath $auxPath -Encoding utf8 | Where-Object { $_ -match '^\\(?:citation|bibdata|bibstyle)\{' } | Sort-Object -Unique
        $bibChanged = ($before -join "`n") -cne ($after -join "`n")
        if ($bibChanged) { Run-SlcTool bibtex $bibArgs }
        # Once the glossary is first rendered, its internal links add index
        # records too. Rebuild it before the final convergence passes.
        if ($pass -eq 2) { Run-SlcTool makeindex $indexArgs }
        $log = Get-Content -LiteralPath $logFile -Raw -Encoding utf8
        $warnings = @($checks | Where-Object { $log -match $_ })
        if ($pass -ge 3 -and -not $bibChanged -and $warnings.Count -eq 0) { break }
        if ($pass -eq 7 -and $bibChanged) { throw 'Bibliography input did not stabilize.' }
    }
    $receipt.remaining_log_checks = $warnings
    if ($warnings.Count -gt 0) { throw "Unsettled final TeX log: $($warnings -join '; ')." }
    $bibliographyLog = Get-Content -LiteralPath (Join-Path $stage "$jobname.blg") -Raw -Encoding utf8
    $glossaryLog = Get-Content -LiteralPath (Join-Path $stage "$jobname.glg") -Raw -Encoding utf8
    if ($bibliographyLog -match "I didn.t find a database entry") { throw 'A citation is missing from the bibliography database.' }
    if ($glossaryLog -match '\b[1-9]\d* (?:entries|entry) rejected\b') { throw 'MakeIndex rejected glossary records.' }
    $pdf = Join-Path $stage "$jobname.pdf"
    $receipt.pdf_sha256 = (Get-FileHash -LiteralPath $pdf).Hash.ToLowerInvariant()
    $receipt.pdf_bytes = (Get-Item -LiteralPath $pdf).Length
    $receipt.status = 'compiled'
} catch {
    if ($receipt.status -ne 'slot_occupied') { $receipt.status = 'failed' }
    $receipt.error = $_.Exception.Message
    throw
} finally {
    if ($insideStage) { Pop-Location }
    foreach ($name in $envBefore.Keys) { [Environment]::SetEnvironmentVariable($name, $envBefore[$name], 'Process') }
    if ($mutex) {
        if ($held) { $mutex.ReleaseMutex(); $receipt.released = $true }
        $mutex.Dispose()
    }
    if ($portableLock) { $portableLock.Dispose(); $receipt.released = $true }
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding utf8
    Write-Output $receiptPath
}
