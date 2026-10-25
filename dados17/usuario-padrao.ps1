param([Parameter(Mandatory=$true)][string]$Python, [Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference = 'Stop'
$out = (Resolve-Path $OutputDir).Path
$testUser = 'sfci' + [guid]::NewGuid().ToString('N').Substring(0,10)
$scratch = Join-Path $env:SystemRoot ('Temp\SantafeSemAdmin-' + [guid]::NewGuid().ToString('N'))
# Disposable credential belongs only to this isolated CI runner. Never log it.
$secret = ConvertTo-SecureString ('Sf!9' + [guid]::NewGuid().ToString('N') + 'zA!') -AsPlainText -Force
$sid = $null
try {
  New-Item -ItemType Directory -Path $scratch | Out-Null
  $account = New-LocalUser -Name $testUser -Password $secret -Description 'Santafe isolated MSI standard user test' -AccountNeverExpires
  $sid = $account.SID.Value
  Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $testUser
  & icacls.exe $scratch /grant ('*' + $sid + ':(OI)(CI)M') | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Cannot grant test account access to its own scratch directory' }
  Copy-Item (Join-Path $out 'santafe-dados17-windows-x64.msi') (Join-Path $scratch 'santafe.msi')
  Copy-Item (Join-Path $out 'santafe-dados17-windows-x64.json') (Join-Path $scratch 'manifesto.json')
  Copy-Item (Join-Path $PSScriptRoot 'usuario-padrao.py') (Join-Path $scratch 'usuario-padrao.py')
  $credential = [pscredential]::new(($env:COMPUTERNAME + '\' + $testUser),$secret)
  $child = Start-Process -FilePath $Python -ArgumentList @(('"' + (Join-Path $scratch 'usuario-padrao.py') + '"'),('"' + $scratch + '"')) -Credential $credential -LoadUserProfile -WorkingDirectory $scratch -PassThru
  if (-not $child.WaitForExit(360000)) { $child.Kill(); throw 'Standard user test timed out' }
  $child.Refresh()
  if ($child.ExitCode -ne 0) { throw ('Standard user test failed: ' + $child.ExitCode) }
} finally {
  if (Test-Path $scratch) {
    Get-ChildItem $scratch -File | Where-Object { $_.Extension -in '.log','.json' -and $_.Name -ne 'manifesto.json' } | Copy-Item -Destination $out
  }
  if ($sid) {
    Get-CimInstance Win32_UserProfile -Filter "SID='$sid'" | Remove-CimInstance -ErrorAction Continue
    Remove-LocalUser -Name $testUser -ErrorAction Continue
  }
  if (Test-Path $scratch) { Remove-Item -LiteralPath $scratch -Recurse -Force }
}
