param([Parameter(Mandatory=$true)][string]$OutputDir, [Parameter(Mandatory=$true)][string]$ToolsDir)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'verificar-assinatura.ps1')
$out=(Resolve-Path $OutputDir).Path
$tools=(Resolve-Path $ToolsDir).Path
$result=[ordered]@{ candidato='dados.20'; testes=@(); assinatura_publica=$false; resultado='em_execucao'; producao_alterada=$false }
$cert=$null
try {
  $package=Join-Path $out 'santafe-dados20-windows-x64.msi'
  $hash=(Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash
  $check=Test-SantafeSignature -Arquivo $package -HashEsperado $hash -SignatarioEsperado ('1'*40)
  if ($check.aprovada -or $check.motivo -ne 'sem_assinatura') { throw 'Unsigned candidate was not refused' }
  $result.testes+=@{ nome='candidato-sem-assinatura-recusado'; passou=$true; evidencia=$check }
  $check=Test-SantafeSignature -Arquivo $package -HashEsperado ('0'*64) -SignatarioEsperado ('1'*40)
  if ($check.aprovada -or $check.motivo -ne 'hash_divergente') { throw 'Wrong hash accepted' }
  $result.testes+=@{ nome='hash-divergente-recusado'; passou=$true }
  # Read the real Windows version resources of our six PE files.
  $runtime=Join-Path $tools 'portatil-renomeado'
  $own=@('bin/santafe.exe','bin/santafec.exe','bin/santafe-sls.exe','bin/santafe-3.dll','share/santafé/1.0/ferramentas/sls/nativo.dll','share/santafé/1.0/ferramentas/pacotes/nativo.dll')
  foreach ($rel in $own) {
    $v=[Diagnostics.FileVersionInfo]::GetVersionInfo((Join-Path $runtime $rel))
    if ($v.ProductName -ne 'Santafé' -or $v.ProductVersion -ne '3.0.20.0' -or $v.FileVersion -ne '3.0.20.0' -or -not $v.IsPreRelease -or -not $v.OriginalFilename) { throw ('Version resource incomplete: '+$rel) }
    $result.testes+=@{ nome=('metadados-'+$rel); passou=$true; produto=$v.ProductName; versao=$v.ProductVersion }
  }
  # Positive control from the official Windows SDK already installed in CI.
  $sdk=Join-Path ${env:ProgramFiles(x86)} 'Windows Kits/10/bin'
  $signtool=Get-ChildItem $sdk -Filter signtool.exe -Recurse | Where-Object { $_.FullName -match '\\x64\\signtool.exe$' } | Sort-Object FullName -Descending | Select-Object -First 1
  if (-not $signtool) { throw 'Official Windows SDK SignTool unavailable' }
  $sig=Get-AuthenticodeSignature -LiteralPath $signtool.FullName
  if (-not $sig.SignerCertificate) { throw 'SDK signature missing' }
  $check=Test-SantafeSignature -Arquivo $signtool.FullName -HashEsperado (Get-FileHash $signtool.FullName -Algorithm SHA256).Hash -SignatarioEsperado $sig.SignerCertificate.Thumbprint
  if (-not $check.aprovada) { throw ('SDK positive control failed: '+($check | ConvertTo-Json -Compress)) }
  $result.testes+=@{ nome='controle-positivo-sdk-assinado'; passou=$true; evidencia=$check }
  $check=Test-SantafeSignature -Arquivo $signtool.FullName -HashEsperado (Get-FileHash $signtool.FullName -Algorithm SHA256).Hash -SignatarioEsperado ('1'*40)
  if ($check.aprovada -or $check.motivo -ne 'signatario_divergente') { throw 'Wrong publisher accepted' }
  $result.testes+=@{ nome='signatario-divergente-recusado'; passou=$true }
  # Test key is non-exportable, never trusted, never used on delivered files.
  $fixture=Join-Path $out 'fixture-assinatura.exe'
  Copy-Item (Join-Path $runtime 'bin/santafe.exe') $fixture
  $cert=New-SelfSignedCertificate -Subject ('CN=Santafe-TESTE-'+[guid]::NewGuid().ToString('N')) -Type CodeSigningCert -KeyExportPolicy NonExportable -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddDays(1)
  $null=Set-AuthenticodeSignature -LiteralPath $fixture -Certificate $cert -HashAlgorithm SHA256
  $sig=Get-AuthenticodeSignature -LiteralPath $fixture
  if ($sig.SignerCertificate.Thumbprint -ne $cert.Thumbprint) { throw 'Test signature was not embedded' }
  $check=Test-SantafeSignature -Arquivo $fixture -HashEsperado (Get-FileHash $fixture -Algorithm SHA256).Hash -SignatarioEsperado $cert.Thumbprint
  if ($check.aprovada -or $check.motivo -ne 'nao_confiavel') { throw 'Untrusted certificate accepted' }
  $result.testes+=@{ nome='autoassinado-nao-confiavel-recusado'; passou=$true; evidencia=$check }
  if ((Get-FileHash $package -Algorithm SHA256).Hash -ne $hash) { throw 'Original MSI changed' }
  $result.resultado='passou_verificacao_assinatura_e_metadados'
} catch {
  $result.resultado='falhou';$result.falha=$_.Exception.Message;throw
} finally {
  if ($cert) { Remove-Item -LiteralPath ('Cert:\CurrentUser\My\'+$cert.Thumbprint) -DeleteKey }
  if ($fixture -and (Test-Path $fixture)) { Remove-Item -LiteralPath $fixture }
  $result | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $out 'assinatura.json')
}
