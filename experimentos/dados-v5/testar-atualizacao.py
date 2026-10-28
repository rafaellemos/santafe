#!/usr/bin/env python3
"""Atualização dados.4 → dados.5 → rollback, em prefixo temporário próprio.

Não homologa downgrade para 2.1 estável. A cópia SLS da geração 4 recebe só
o fechamento de arquivos/relocação corrigido no 5, necessário para instalá-la.
Nenhum arquivo da árvore anterior é escrito.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]; old=Path(sys.argv[1]).resolve()
assert (ROOT/'.laboratorio-dados5').is_file() and (old/'.laboratorio-dados4').is_file()
lab=Path(tempfile.mkdtemp(prefix='santafe-atualizacao5-',dir='/tmp'))
prefix=lab/'instalacao'; backup=lab/'anterior'
env={k:os.environ[k] for k in ('PATH','TMPDIR','LANG','LC_ALL') if k in os.environ}
env['GSETTINGS_BACKEND']='memory'; platform='macosx' if sys.platform=='darwin' else 'linux'
def run(args,cwd=ROOT):
    p=subprocess.run(args,cwd=cwd,env=env,text=True,capture_output=True,timeout=45)
    assert p.returncode==0,p.stdout+p.stderr
    return p
def copy(source):
    for stage in ('bin','pacotes','c','fe','pc'):
        run(['bash',str(ROOT/'ferramentas/instalar-arquivos.sh'),stage,str(prefix),platform,
             '0.0.0-dados.4' if source==old else '0.0.0-dados.5'],source)
    folder=prefix/'share/santafé/1.0/ferramentas'; sls=folder/'sls'; sls.mkdir(exist_ok=True)
    for name in ('analisador.fé','projetos.fé','semantica.fé','transporte.fé','estrutura.fé','api-publica.json'):
        shutil.copy2(source/'ferramentas/sls'/name,sls/name)
    # Dados.4 traz o suporte SLS embutido no binário (exercitado por health).
    native=source/'ferramentas/sls/nativo.so'
    if native.exists(): shutil.copy2(native,sls/'nativo.so')
    text=(source/'ferramentas/sls/sls.fé').read_text().replace('/../../experimentos/dados-v1/onfé.fé','/onfé.fé')
    (folder/'sls.fé').write_text(text)
    shutil.copy2(source/'experimentos/dados-v1/onfé.fé',sls/'onfé.fé')
def hashes():
    return {str(p.relative_to(prefix)):hashlib.sha256(p.read_bytes()).hexdigest() for p in prefix.rglob('*') if p.is_file()}
def health(revision):
    v=run([str(prefix/'bin/santafé'),'-v'],lab)
    assert 'candidato-dados.'+revision in v.stdout+v.stderr
    code='local O=executeArquivo("'+str(prefix)+'/share/santafé/1.0/ferramentas/sls/onfé.fé"); local f=garanta(es.abra("'+str(lab)+'/dados.onfé","leitura")); local x=O.decod(f:leia("*tudo")); f:feche(); garanta(tipo(x.itens)=="lista" e #x.itens==3 e tabela.temChave(x,"valor") e x.valor==nulo); garanta(O.paraJSON(x):procure("null",1,verdadeiro)); mostre("persistência ok")'
    run([str(prefix/'bin/santafé'),'-E','-P','-e',code],lab)
    sys.path.insert(0,str(ROOT/'testes/integracao'))
    from sls.cliente import Cliente
    c=Cliente([str(prefix/'bin/santafé-sls')],lab)
    try: c.inicie(); assert c.informacao['version']=='1.0.0-dados.'+revision
    finally: c.feche()

copy(old)
(lab/'dados.onfé').write_text('{valor=nulo,itens=[1,nulo,3],texto=[=[não alterar]=]}')
payload=(lab/'dados.onfé').read_bytes()
foreign=prefix/'local-do-usuario.txt'; foreign.write_text('preservar')
health('4'); before=hashes(); shutil.copytree(prefix,backup)
copy(ROOT); health('5'); assert foreign.read_text()=='preservar'
prefix.rename(lab/'nova-preservada'); backup.rename(prefix)
health('4'); assert hashes()==before and (lab/'dados.onfé').read_bytes()==payload
result={'resultado':'PASSOU','origem':'dados.4','destino':'dados.5','retorno':'dados.4',
        'prefixo':str(prefix),'arquivos_verificados':len(before),
        'limite':'SLS anterior com fechamento de arquivos/relocação; não é downgrade da versão maior para 2.1'}
(ROOT/'evidencias/atualizacao5.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('PASSOU atualização 4→5→4; hashes exatos, SLS, ONFÉ e arquivos próprios preservados:',lab)
