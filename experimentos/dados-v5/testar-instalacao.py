#!/usr/bin/env python3
"""Copia artefatos reais em prefixo privado; falhas reais e rollback por snapshot.

Não é o publicador de produção. Não invoca sudo/instalar.sh nem baixa deps.
O núcleo já foi compilado com ABI experimental por construir.sh.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados5').is_file()
sys.path.insert(0,str(ROOT/'testes/integracao'))
from sls.cliente import Cliente

lab=Path(tempfile.mkdtemp(prefix='santafe-instalacao5-',dir='/tmp'))
prefix=lab/'prefixo com espaços'
env={k:os.environ[k] for k in ('PATH','TMPDIR','LANG','LC_ALL') if k in os.environ}
env['GSETTINGS_BACKEND']='memory'
platform='macosx' if sys.platform=='darwin' else 'linux'
stages=('bin','sls','pacotes','c','fe','pc')
results=[]
def run(args, **kw):
    return subprocess.run(args,cwd=kw.pop('cwd',ROOT),env=env,text=True,capture_output=True,check=True,timeout=45,**kw)
def copy(stage, source=ROOT):
    return run(['bash',str(ROOT/'ferramentas/instalar-arquivos.sh'),stage,str(prefix),platform,'0.0.0-dados.22'],cwd=source)
def passed(name): results.append(name); print('PASSOU',name,flush=True)
def digest(directory):
    return {str(p.relative_to(directory)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode&0o777)
            for p in directory.rglob('*') if p.is_file()}
def healthy():
    binary=prefix/'bin/santafé'
    v=run([str(binary),'-E','-P','-v'],cwd=lab)
    assert '3.0.0' in v.stdout+v.stderr
    bootstrap='módulo.caminho="'+str(prefix)+'/share/santafé/3.0/bibf/?.fé;'+str(prefix)+'/share/santafé/3.0/bibf/?/?.fé"; módulo.caminhoC="'+str(prefix)+'/lib/santafé/3.0/bibc/?.so"'
    code='; '.join('garanta(importe "'+name+'")' for name in ('arquivo','rede','segredo','mariadb','tomada','correio.imap','nomes','rpdf','vigia'))
    code+='; garanta(tipo([nulo])=="lista"); local t={x=nulo}; garanta(tabela.temChave(t,"x")); garanta(json.cod([nulo])=="[null]")'
    code+='; local O=importe "onfé"; local ok,f,s=O.grave("persistencia-instalada.onfé",{v=nulo,itens=[]}); garanta(ok e s=="durável"); local v=O.carregue("persistencia-instalada.onfé"); garanta(tabela.temChave(v,"v") e tipo(v.itens)=="lista")'
    run([str(binary),'-E','-P','-e',bootstrap,'-e',code],cwd=lab)
    pc=(prefix/'lib/pkgconfig/santafe.pc').read_text(); assert 'Version: 0.0.0-dados.22\n' in pc
    assert 'prefix='+str(prefix)+'\n' in pc
    help=run([str(binary),'instale','--ajuda'],cwd=lab); assert 'instale' in help.stdout
    workspace=lab/'projeto'; workspace.mkdir(exist_ok=True)
    c=Cliente([str(prefix/'bin/santafé-sls')],workspace)
    try:
        c.inicie(); assert c.informacao['version']=='1.1.0'
        uri=c.abra('local lista=[nulo,"José"]\nlocal t={v=nulo}\n','instalado.fé')
        assert not c.diagnosticos(uri)
        uri=c.abra('{lista=[nulo],objeto={nome="José"},bruto=[=[ação\n®literal]=]}','dados.onfé')
        assert not c.diagnosticos(uri)
    finally: c.feche()

try:
    blocked=subprocess.run(['bash',str(ROOT/'instalar.sh'),'--sem-dependencias','--prefixo',str(lab/'nao-instalar')],
        cwd=ROOT,env=env,text=True,capture_output=True,timeout=5)
    assert blocked.returncode==2 and 'instalação pública indisponível' in blocked.stderr
    assert not (lab/'nao-instalar').exists()
    blocked=subprocess.run(['make','-n','instalar'],cwd=ROOT,env=env,text=True,capture_output=True,timeout=5)
    assert blocked.returncode!=0 and 'Candidato dados.23' in blocked.stderr
    passed('candidato bloqueia instalador público e Makefile estável antes de efeitos')
    for stage in stages: copy(stage)
    healthy(); passed('instalação completa em prefixo com espaços; núcleo, 5 bibC, Fé, CLI, SLS e ONFÉ')
    foreign=prefix/'share/santafé/3.0/bibf/arquivo-do-usuario.txt'; foreign.write_text('preservar')
    original=digest(prefix)
    for stage in stages: copy(stage)
    healthy(); assert digest(prefix)==original
    passed('reinstalação/atualização idempotente sem remover arquivos alheios')
    # Falha genuína de cópia: fonte sem analisador; usa o instalador real.
    incomplete=lab/'fonte incompleta'; (incomplete/'ferramentas/sls').mkdir(parents=True)
    shutil.copy2(ROOT/'ferramentas/sls/sls.fé',incomplete/'ferramentas/sls/sls.fé')
    for failure in (*stages,'copia-ausente','saude'):
        backup=lab/('backup-'+failure); shutil.copytree(prefix,backup)
        try:
            for stage in stages:
                copy(stage,incomplete if stage=='sls' and failure=='copia-ausente' else ROOT)
                if stage==failure:
                    # Modificação no candidato em transição torna a restauração verificável.
                    (prefix/'bin/marcador-atualizacao').write_text(failure)
                    raise RuntimeError('interrupção injetada após '+stage)
            if failure=='saude':
                (prefix/'share/santafé/3.0/ferramentas/sls/onfé.fé').write_text('erro("falha de saúde injetada")')
                healthy()
            raise AssertionError('falha não exercitada')
        except (subprocess.CalledProcessError,RuntimeError,AssertionError,BrokenPipeError) as exc:
            assert str(exc)!='falha não exercitada'
            broken=lab/('interrompido-'+failure)
            prefix.rename(broken); backup.rename(prefix)
            assert digest(prefix)==original, failure
            healthy()
    passed('rollback exato após 6 etapas, cópia ausente e falha de saúde do SLS')
    # Artefatos e arquivos terceiros verificáveis depois de remover só o que pertence à distribuição.
    for stage in ('bin','bibs'):
        run(['bash',str(ROOT/'ferramentas/desinstalar-arquivos.sh'),stage,str(prefix),platform])
    assert foreign.read_text()=='preservar'
    assert not (prefix/'bin/santafé').exists()
    assert not (prefix/'share/santafé/3.0/ferramentas/sls/onfé.fé').exists()
    assert not (prefix/'share/santafé/3.0/bibf/onfé.fé').exists()
    assert not (prefix/'share/santafé/3.0/ferramentas/sls/estrutura.fé').exists()
    passed('desinstalação remove suporte SLS/ONFÉ e preserva arquivo do usuário')
finally:
    (ROOT/'evidencias').mkdir(exist_ok=True)
    (ROOT/'evidencias/instalacao5.json').write_text(json.dumps({'passaram':results,'esperados':5,'laboratorio':str(lab)},ensure_ascii=False,indent=2)+'\n')
    print('Prefixos e snapshots preservados em',lab,flush=True)
