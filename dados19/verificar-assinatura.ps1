function Test-SantafeSignature {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory=$true)][string]$Arquivo,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{64}$')][string]$HashEsperado,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{40}$')][string]$SignatarioEsperado
  )
  $item = Get-Item -LiteralPath $Arquivo -ErrorAction Stop
  if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Arquivo regular exigido' }
  $before = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash
  $result = [ordered]@{ arquivo=$item.Name; sha256=$before; aprovada=$false; motivo=''; status_windows=$null; signatario=$null; carimbo=$false }
  if ($before -ne $HashEsperado) { $result.motivo='hash_divergente'; return [pscustomobject]$result }
  $sig = Get-AuthenticodeSignature -LiteralPath $item.FullName
  $result.status_windows = [string]$sig.Status
  if ($sig.SignerCertificate) { $result.signatario=$sig.SignerCertificate.Thumbprint }
  $result.carimbo = $null -ne $sig.TimeStamperCertificate
  if ($sig.Status -eq 'NotSigned') { $result.motivo='sem_assinatura' }
  elseif ($sig.Status -ne 'Valid') { $result.motivo='nao_confiavel' }
  elseif ($sig.SignatureType -ne 'Authenticode') { $result.motivo='assinatura_embutida_exigida' }
  elseif ($sig.SignerCertificate.Thumbprint -ne $SignatarioEsperado) { $result.motivo='signatario_divergente' }
  elseif ('1.3.6.1.5.5.7.3.3' -notin @(($sig.SignerCertificate.Extensions | Where-Object { $_.Oid.Value -eq '2.5.29.37' }).EnhancedKeyUsages.Value)) { $result.motivo='uso_de_codigo_exigido' }
  elseif (-not $sig.TimeStamperCertificate) { $result.motivo='sem_carimbo' }
  elseif ((Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash -ne $before) { $result.motivo='arquivo_alterado_durante_verificacao' }
  else { $result.motivo='validada_pelo_windows'; $result.aprovada=$true }
  return [pscustomobject]$result
}
