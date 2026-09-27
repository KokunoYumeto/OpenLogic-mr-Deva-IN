param([int]$SlotTimeoutMilliseconds = 1500)
$ErrorActionPreference = 'Stop'
$mutex = [Threading.Mutex]::new($false, 'Global\InterlanguageTeXSlotV1')
$held = $false
try {
  try { $held = $mutex.WaitOne($SlotTimeoutMilliseconds) }
  catch [Threading.AbandonedMutexException] { $held = $true }
  if (-not $held) { Write-Output 'slot-occupied'; return }
  $logPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\build\core\openlogic-mr-core.log'))
  $log = Get-Content -LiteralPath $logPath -Raw
  $matches = [regex]::Matches($log, '(?m)^.*?:\d+: (?:Missing \$ inserted|Undefined control sequence|LaTeX Error|Paragraph ended)')
  if ($matches.Count -eq 0) { Write-Output 'no-matched-error'; return }
  $first = $matches[0]
  $start = [Math]::Max(0, $first.Index - 800)
  $length = [Math]::Min(2200, $log.Length - $start)
  Write-Output $log.Substring($start, $length)
} finally {
  if ($held) { $mutex.ReleaseMutex() }
  $mutex.Dispose()
}
