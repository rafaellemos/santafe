param([Parameter(Mandatory=$true)][string]$Python, [Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference = 'Stop'
# This fixture may configure only a disposable GitHub-hosted Windows machine.
# The MSI itself must never change this policy or elevate the installing user.
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_ENVIRONMENT -ne 'github-hosted') { throw 'Disposable GitHub-hosted runner required' }
$policyKey = 'HKLM:\Software\Policies\Microsoft\Windows\Installer'
$hadKey = Test-Path $policyKey
$hadPolicy = $false
$oldPolicy = $null
$oldPolicyKind = $null
if ($hadKey) {
  $key = Get-Item $policyKey
  $hadPolicy = $key.GetValueNames() -contains 'DisableMSI'
  if ($hadPolicy) { $oldPolicy = $key.GetValue('DisableMSI'); $oldPolicyKind = $key.GetValueKind('DisableMSI') }
}
$policyTouched = $false
function Run-StandardChild([string]$Mode) {
  $arguments = @(('"' + (Join-Path $scratch 'usuario-padrao.py') + '"'),('"' + $scratch + '"'))
  if ($Mode) { $arguments += $Mode }
  $child = Start-Process -FilePath $Python -ArgumentList $arguments -Credential $credential -LoadUserProfile -WorkingDirectory $scratch -PassThru
  if (-not $child.WaitForExit(360000)) { $child.Kill(); throw 'Standard user test timed out' }
  $child.Refresh()
  if ($child.ExitCode -ne 0) { throw ('Standard user test failed: ' + $child.ExitCode) }
}

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
  if (-not $hadKey) { New-Item -Path $policyKey -Force | Out-Null }
  $policyTouched = $true
  New-ItemProperty -Path $policyKey -Name DisableMSI -Value 1 -PropertyType DWord -Force | Out-Null
  Run-StandardChild 'politica-bloqueia'
  New-ItemProperty -Path $policyKey -Name DisableMSI -Value 0 -PropertyType DWord -Force | Out-Null
  Run-StandardChild ''
} finally {
  if ($policyTouched) {
    if ($hadPolicy) { Set-ItemProperty -Path $policyKey -Name DisableMSI -Value $oldPolicy -Type $oldPolicyKind }
    else { Remove-ItemProperty -Path $policyKey -Name DisableMSI }
    if (-not $hadKey -and (Get-Item $policyKey).GetValueNames().Count -eq 0 -and (Get-Item $policyKey).SubKeyCount -eq 0) { Remove-Item $policyKey }
    $restored = if ($hadPolicy) { (Get-Item $policyKey).GetValue('DisableMSI') -eq $oldPolicy } else { -not ((Test-Path $policyKey) -and ((Get-Item $policyKey).GetValueNames() -contains 'DisableMSI')) }
    @{ restaurada=$restored; valor_anterior=$oldPolicy; existia_antes=$hadPolicy; configuracoes_testadas=@(1,0); alteracao_somente_ci=$true } | ConvertTo-Json | Set-Content (Join-Path $out 'politica-ci.json')
    if (-not $restored) { throw 'MSI test policy was not restored' }
  }
  if (Test-Path $scratch) {
    Get-ChildItem $scratch -File | Where-Object { $_.Extension -in '.log','.json' -and $_.Name -ne 'manifesto.json' } | Copy-Item -Destination $out
  }
  if ($sid) {
    Get-CimInstance Win32_UserProfile -Filter "SID='$sid'" | Remove-CimInstance -ErrorAction Continue
    Remove-LocalUser -Name $testUser -ErrorAction Continue
  }
  if (Test-Path $scratch) { Remove-Item -LiteralPath $scratch -Recurse -Force }
}
