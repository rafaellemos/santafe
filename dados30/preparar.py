"""Prepara a embalagem final Windows sem alterar o código já homologado25."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile

repo=Path(__file__).resolve().parent.parent
source=repo/'fonte'
archive=repo/'dados30/fonte-final.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='5bf259822c334ee5f548cac8ac75ac61e88258445b83bcf43f57a064d84a0e28'
assert not source.exists()
rows={}
with tarfile.open(archive) as package:
    total=0
    for member in package:
        n=Path(member.name)
        assert member.isfile() and not n.is_absolute() and '..' not in n.parts
        assert str(n).replace('\\','/')==member.name and '\\' not in member.name and ':' not in member.name
        assert member.name not in rows and member.size<=32*1024**2
        total+=member.size;assert total<=128*1024**2
        rows[member.name]=(package.extractfile(member).read(),member.mode&0o755)
manifest=json.loads(rows['MANIFESTO-FONTES.json'][0])
assert manifest=={n:hashlib.sha256(b).hexdigest() for n,(b,_) in rows.items() if n!='MANIFESTO-FONTES.json'}
assert len(manifest)==911
for n,(data,mode) in rows.items():
    p=source/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(mode)
# Selecionar o contrato dos dados3 para a identidade final, sem afrouxar
# verificações comportamentais do SLS (mesmo ajuste do ensaio25).
p=source/'testes/integracao/sls/casos.py';s=p.read_text(encoding='utf-8')
old='"dados." in c.informacao.get("version", "")'
assert s.count(old)==2
p.write_text(s.replace(old,'("dados." in c.informacao.get("version", "") or c.informacao.get("version") == "1.1.0")'),encoding='utf-8')
(source/'PREPARACAO-WINDOWS.json').write_text(json.dumps({'versao':'3.0.0','fonte_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'arquivos':len(manifest),'codigo_inalterado':True})+'\n',encoding='utf-8')

# Reaproveitar os critérios25 de núcleo/ferramentas. O MSI final tem canal
# próprio; candidatos3.0.25 continuam isolados e não são tratados como3.0.0.
subprocess.run([sys.executable,str(repo/'dados25/preparar-bateria.py')],check=True)
dest=repo/'apoio30';assert not dest.exists()
shutil.copytree(repo/'apoio25',dest)
for p in dest.rglob('*'):
    if p.suffix not in ('.py','.ps1') or 'base21' in p.parts or 'base' in p.parts:continue
    s=p.read_text(encoding='utf-8')
    s=s.replace('santafe-dados25-windows-x64','santafe-3.0.0-windows-x64')
    p.write_text(s,encoding='utf-8')

def edit(name,old,new,count=None):
    p=dest/name;s=p.read_text(encoding='utf-8')
    assert old in s,(name,old)
    if count is not None:assert s.count(old)==count,(name,old,s.count(old))
    p.write_text(s.replace(old,new),encoding='utf-8')

edit('recursos.py','3.0.25.0','3.0.0.0')
edit('recursos.py','3,0,25,0','3,0,0,0')
edit('recursos.py','FILEFLAGS VS_FF_PRERELEASE','FILEFLAGS 0')
edit('recursos.py','Candidato dados.25; uso exclusivo em homologação.','Santafé 3.0.0; núcleo, SLS e gerenciador.')
edit('portatil.py','Santafé dados.25 — candidato Windows x64, não versão estável.','Santafé 3.0.0 — Windows x64; SLS 1.1.0 e gerenciador 1.1.0.')
edit('portatil.py','Nenhuma modalidade instala serviços. Usar somente em homologação.','Nenhuma modalidade instala serviços. Instalador sem assinatura Authenticode; confira a origem e o SHA-256 no portal oficial.')
edit('portatil.py','Este pacote25 exige sua própria homologação; resultados visuais21 são históricos.','Windows 10/11: validação visual do candidato com o mesmo código; a identidade final e o instalador têm testes próprios registrados.')
edit('portatil.py',"'versao_estavel':False","'versao_estavel':True")

# Critérios MSI20 já exercitados. Fixture16 é empacotada como2.9.0 no canal
# final só para comprovar atualização/reversão; não é uma versão pública2.9.
shutil.copyfile(repo/'dados20/msi.py',dest/'msi.py')
for old,new in [
 ("candidate-windows-x64-channel","stable-windows-x64-channel"),
 ("Software\\Santafe\\CandidatoDados","Software\\Santafe\\Estavel"),
 ("tuple(map(int,version.split('.'))) >= (3,0,19)","tuple(map(int,version.split('.'))) >= (3,0,0)"),
 ("guid('product-'+version","guid('stable-product-'+version"),
 ("guid('component/'+name)","guid('stable-component/'+name)"),
 ("guid('registration')","guid('stable-registration')"),
 ('Santafé dados — candidato Windows','Santafé 3 — Windows'),
 ('Candidato isolado; não instala serviços.','Núcleo, SLS e gerenciador; instalação por usuário, sem serviços.'),
 ('Santafe-Dados-Candidato','Santafe-3'),('Santafe Candidato','Santafe'),
 ('Santafe candidato','Santafe'),('Santafé — candidato','Santafé — instalação'),
 ('Candidato de homologação, sem assinatura Authenticode; não instala serviços.','Sem assinatura Authenticode; confira a origem e o SHA-256 no portal oficial. Não instala serviços.'),
 ('Este candidato aceita instalação por usuário.','Esta distribuição aceita instalação por usuário.'),
 ("'dados.20' if version=='3.0.20'","'3.0.0' if version=='3.0.0'")]:edit('msi.py',old,new)
shutil.copyfile(repo/'dados20/testar-instalador.py',dest/'testar-instalador.py')
for old,new in [
 ('santafe-dados20-windows-x64','santafe-3.0.0-windows-x64'),
 ("'3.0.16'","'2.9.0'"),("'3.0.20'","'3.0.0'"),("'3.0.21'","'3.0.1'"),
 ('Santafe-Dados-Candidato','Santafe-3'),('/santafé/1.0/','/santafé/3.0/'),
 ("'candidato':'dados.20'","'distribuicao':'3.0.0', 'baseline':'fixture dados16 reempacotada como2.9.0; não é versão pública'")]:edit('testar-instalador.py',old,new)
edit('testar-assinatura.ps1','3.0.25.0','3.0.0.0')
p=dest/'testar-assinatura.ps1';s=p.read_text(encoding='utf-8')
assert s.count('-not $v.IsPreRelease')==1
s=s.replace('-not $v.IsPreRelease','$v.IsPreRelease')
p.write_text(s,encoding='utf-8')
for p in dest.rglob('*.py'):compile(p.read_text(encoding='utf-8'),str(p),'exec')
print('EMBALAGEM3_PREPARADA: código final conferido; canal separado; mesmas proteções; sem assinatura pública')

# O canal padrão conserva o prefixo validado pela guarda, sem relaxá-la.
edit('usuario-padrao.py','Programs/Santafe-Dados-Candidato','Programs/Santafe-3')
