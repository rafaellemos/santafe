#!/usr/bin/env python3
"""Geração estável real → candidata → retorno, crashes e leitores concorrentes."""
import concurrent.futures, json, os, shutil, subprocess, sys, time
from pathlib import Path
from operacao import new, stage, seal, activate, current, locked, recover, hashes, generation
ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados6').is_file()
baseline=Path(sys.argv[1]).resolve(); lab=new(); results=[]
env={k:os.environ[k] for k in ('PATH','TMPDIR','LANG','LC_ALL') if k in os.environ}
def run(binary,code):
    return subprocess.run([str(binary),'-E','-P','-e',code],env=env,cwd=lab,capture_output=True,text=True,check=True,timeout=15).stdout
def version(binary):
    p=subprocess.run([str(binary),'-E','-P','-v'],env=env,cwd=lab,capture_output=True,text=True,check=True,timeout=15)
    return p.stdout+p.stderr
assert '2.1.0' in version(baseline)
old=lab/'geracoes/estavel'; (old/'bin').mkdir(parents=True)
shutil.copy2(baseline,old/'bin/santafé'); seal(old)
candidate=stage(lab,ROOT,'candidata')
data=lab/'dados/arquivo.json'; data.write_text('{"valor":null,"lista":[]}')
def health(p):
    text=version(p/'bin/santafé')
    assert ('2.1.0' if p.name=='estavel' else '3.0.0') in text, text
    if p.name!='estavel':
        boot='módulo.caminho="'+str(p)+'/share/santafé/3.0/bibf/?.fé;'+str(p)+'/share/santafé/3.0/bibf/?/?.fé"; módulo.caminhoC="'+str(p)+'/lib/santafé/3.0/bibc/?.so"; '
        run(p/'bin/santafé',boot+'garanta(importe "correio.imap"); garanta(importe "arquivo"); local t={x=nulo}; garanta(tabela.temChave(t,"x")); garanta(#json.decod("[null]")==1)')
before=hashes(old); payload=data.read_bytes()
activate(lab,'estavel',health)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    def reader():
        seen=set()
        for _ in range(100):
            # Resolve UMA vez: não mistura núcleo antigo com módulos novos.
            p=(lab/'atual').resolve(); health(p); seen.add(p.name)
        return sorted(seen)
    futures=[pool.submit(reader) for _ in range(3)]
    for _ in range(10): activate(lab,'candidata',health); activate(lab,'estavel',health)
    readers=[f.result() for f in futures]
results.append({'teste':'300 leituras concorrentes; 20 trocas atômicas','leitores':readers})
for fail in ('antes','depois'):
    pid=os.fork()
    if pid==0: activate(lab,'candidata',health,fail); os._exit(99)
    _,status=os.waitpid(pid,0); assert os.WEXITSTATUS(status)==(91 if fail=='antes' else 92)
    with locked(lab): recover(lab)
    assert current(lab)=='estavel'
    results.append({'teste':'recuperação após término abrupto '+fail})
try: activate(lab,'candidata',health,'saude'); raise AssertionError('não injetou')
except RuntimeError: pass
assert current(lab)=='estavel'
results.append({'teste':'rollback pós-saúde'})
with locked(lab):
    code='import sys;sys.path.insert(0,'+repr(str(Path(__file__).parent))+');from operacao import locked;from pathlib import Path\nwith locked(Path('+repr(str(lab))+')): pass'
    p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert p.returncode!=0 and 'BlockingIOError' in p.stderr
results.append({'teste':'segundo escritor bloqueado'})
(candidate/'biblioteca').mkdir()
nested=candidate/'biblioteca/manifesto.json'
nested.write_text('{"original":true}'); seal(candidate)
nested.write_text('{"original":false}')
try: activate(lab,'candidata',health); raise AssertionError('manifesto interno não conferido')
except AssertionError as e: assert str(e)=='integridade da geração'
assert current(lab)=='estavel'
results.append({'teste':'manifesto interno de biblioteca também coberto pela integridade'})
nested.write_text('{"original":true}'); seal(candidate)
(candidate/'corrompido').write_text('não publicar')
try: activate(lab,'candidata',health); raise AssertionError('integridade não conferida')
except AssertionError as e: assert str(e)=='integridade da geração'
assert current(lab)=='estavel' and hashes(old)==before and data.read_bytes()==payload
results.append({'teste':'integridade recusada; estável e dados preservados'})
(ROOT/'evidencias').mkdir(exist_ok=True)
(ROOT/'evidencias/operacao6.json').write_text(json.dumps({'resultado':'PASSOU','testes':results,'laboratorio':str(lab),
 'limites':'baseline somente núcleo 2.1; não migra DB, não simula perda elétrica, não troca serviços globais'},ensure_ascii=False,indent=2)+'\n')
print('PASSOU operação:',len(results),'grupos;',lab)
