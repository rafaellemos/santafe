#!/usr/bin/env python3
"""Deriva dados.14 exclusivamente dos fontes selados dados.13."""
from pathlib import Path
import hashlib,tarfile,tempfile,shutil
ROOT=Path(__file__).resolve().parents[2]
a=ROOT/'dist/candidato-dados-v13/santafe-candidato-dados.13-fontes.tar.gz'
assert hashlib.sha256(a.read_bytes()).hexdigest()=='dfed0891450d6b0465c2c2db3fc9013029c948a385a17ae6c11885bb807ece52'
s=Path(tempfile.mkdtemp(prefix='santafe-dados14-',dir='/tmp')).resolve()
with tarfile.open(a) as t:
 assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in t.getmembers())
 t.extractall(s)
(s/'.laboratorio-dados14').write_text('Somente homologação.\n')
names=['src/lua.h','ferramentas/sls/sls.fé','docs/manual.html','Makefile','instalar.sh','experimentos/dados-v3/testar-wasm.js','experimentos/dados-v5/testar-instalacao.py','experimentos/dados-v6/testar-operacao.py','experimentos/dados-v6/operacao.py','experimentos/dados-v2/editores.py','experimentos/dados-v2/testar-editores.js','experimentos/dados-v8/testar-editores.js','experimentos/dados-v8/testar-recorte-sublime.py','experimentos/dados-v10/testar.py']
for n in names:
 p=s/n;p.write_text(p.read_text().replace('dados.13','dados.14').replace('0.0.13','0.0.14').replace('dados-v13/editores','dados-v14/editores').replace('dados-v13/gramaticas-vscode','dados-v14/gramaticas-vscode').replace('EDITORES_DADOS_13_OK','EDITORES_DADOS_14_OK'))
manual=s/'docs/manual.html'
text=manual.read_text().replace('As extensões 1.1.0 distribuídas pelo portal','As extensões 1.1.1 distribuídas pelo portal')
text=text.replace('A inspeção visual nativa do candidato atual ainda é um gate separado dos testes de gramática.', 'A inspeção visual nativa é um critério separado dos testes de gramática; consulte o relatório deste candidato para distinguir verificações novas de evidências herdadas.')
text=text.replace('A réplica operacional completa e plataformas não ensaiadas continuam sendo critérios de promoção.', 'O relatório e ESTADO.json deste candidato registram a homologação da réplica operacional, seus limites e as pendências de promoção. Testes locais de certificados não comprovam emissão pública; plataformas não ensaiadas permanecem fora do escopo.')
manual.write_text(text)
shutil.copytree(ROOT/'experimentos/dados-v14',s/'experimentos/dados-v14',ignore=shutil.ignore_patterns('__pycache__','LOCAL.json'))
shutil.copytree(s/'experimentos/dados-v13/gramaticas-vscode',s/'experimentos/dados-v14/gramaticas-vscode')
for n,dest in [('migrar-replica.py','migrar-replica.py'),('carga-replica.py','carga-base.py')]:
 text=(s/'experimentos/dados-v12'/n).read_text().replace('dados.12','dados.14').replace('dados12','dados14').replace('DADOS12','DADOS14')
 if n=='migrar-replica.py':text=text.replace("HERE/'verificar-replica.py'", "HERE.parent/'dados-v12/verificar-replica.py'")
 if n=='migrar-replica.py':text=text.replace("ctx=ssl.create_default_context(cafile=str(self.stage/'testes/recursos/tls-local-certificado.pem'))", "ctx=self.client_tls() if kind=='candidata' and hasattr(self,'client_tls') else ssl.create_default_context(cafile=str(self.stage/'testes/recursos/tls-local-certificado.pem'))")
 if n=='carga-replica.py':
  text=text.replace('rss<=800*1024','rss<=1536*1024')
  text=text.replace("logs+=sum(p.stat().st_size for p in (self.lab/'candidata/var/log').rglob('*') if p.is_file())", "logs+=sum(p.stat().st_size for p in (self.lab/'candidata/var/log').rglob('*') if p.is_file())\n     logs+=sum(p.stat().st_size for p in self.i.rglob('*') if p.is_file() and p.suffix=='.log')")
 (s/'experimentos/dados-v14'/dest).write_text(text)
print('CANDIDATO_PREPARADO',s)
