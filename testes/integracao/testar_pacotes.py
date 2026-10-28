#!/usr/bin/env python3
"""Integration harness; users need no Python. All fixtures live in mkdtemp."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sls.cliente import Cliente

ROOT = Path(__file__).resolve().parents[2]
SF = ROOT / 'src/santafé'
ENV = {k:os.environ[k] for k in ('PATH','TMPDIR','LANG','LC_ALL') if k in os.environ}
ENV.update(LUA_PATH=str(ROOT/'ferramentas/?.fé'), LUA_CPATH=str(ROOT/'ferramentas/?/?.so'),GSETTINGS_BACKEND='memory')
INIT = ('local N=garanta(módulo.carregarBib('+json.dumps(str(ROOT/'ferramentas/pacotes/nativo.so'),ensure_ascii=False)+',"luaopen_pacotes_nativo"))(); '
        'local F=(importe "pacotes.formatos")(N); local C=(importe "pacotes.cliente")(N,F); '
        'local A=(importe "pacotes.administracao")(N,F); ')

def sf(code, *args, success=True):
    p = subprocess.run([str(SF), '-e', INIT+code, '--', *map(str,args)], env=ENV, text=True, capture_output=True, timeout=35)
    if success and p.returncode:
        raise AssertionError(p.stderr+p.stdout)
    if not success and not p.returncode:
        raise AssertionError('expected failure: '+p.stdout)
    return p

def lit(value):
    return json.dumps(str(value), ensure_ascii=False)

def fixture(root, name='exemplo', version='1.0.0', native=False):
    root.mkdir(parents=True)
    files={'README.md':'# Exemplo\n', 'LICENSE':'MIT\n', 'bibf/exemplo.fé':'local M={valor=42}; função M.somar(a,b) retorne a+b fim; retorne M\n'}
    manifest={'formato':1,'nome':name,'versao':version,'descricao':'Ensaio isolado', 'licenca':'MIT',
              'autores':['Homologação Santafé'], 'fonte':'https://example.invalid/fonte',
              'dependencias':{}, 'modulos':{'exemplo':'bibf/exemplo.fé'},'arquivos':list(files)}
    if native:
        files['src/soma.c']='#include "lua.h"\n#include "lauxlib.h"\n#ifdef SANTAFE_DADOS_V3\nSANTAFE_MODULE_ABI;\n#endif\nstatic int f(lua_State*L){lua_pushinteger(L,luaL_checkinteger(L,1)+luaL_checkinteger(L,2));return 1;}\nint luaopen_soma(lua_State*L){luaL_checkversion(L);lua_pushcfunction(L,f);return 1;}\n'
        manifest['nativos']={'soma':{'fontes':['src/soma.c']}}
        manifest['arquivos']=list(files)
    for path,content in files.items():
        file=root/path; file.parent.mkdir(parents=True,exist_ok=True); file.write_text(content)
    (root/'santafe.json').write_text(json.dumps(manifest,ensure_ascii=False))
    return manifest

def run():
    with tempfile.TemporaryDirectory(prefix='santafe-pacotes-') as temp:
        tmp=Path(temp); repo=tmp/'repo'; repo.mkdir(); project=tmp/'projeto com espaços'; project.mkdir()
        src=tmp/'fonte'; fixture(src)
        sf(f'local b=garanta(A.empacote({lit(src)})); garanta(A.adicione({lit(repo)},b))')
        initial=(repo/'indice.json').read_bytes()
        sf(f'local b=garanta(A.empacote({lit(src)})); garanta(A.adicione({lit(repo)},b))')
        assert initial==(repo/'indice.json').read_bytes()
        options='{repositórioLocal='+lit(repo)+'}'
        sf(f'garanta(C.instale({lit(project)},"exemplo","^1.0.0",{options}))')
        lock=(project/'santafe.lock').read_bytes()
        state=json.loads((project/'.santafe/estado.json').read_text()); generation=project/'.santafe/geracoes'/state['geracao']
        assert 'valor=42' in (generation/'pacotes/exemplo/bibf/exemplo.fé').read_text()
        runtime=subprocess.run([str(SF),'-e','garanta((importe "exemplo").valor==42)'],cwd=project,env=ENV,capture_output=True,text=True)
        assert runtime.returncode==0,runtime.stderr
        bypass=subprocess.run([str(SF),'-P','-e','importe "exemplo"'],cwd=project,env=ENV,capture_output=True,text=True)
        assert bypass.returncode!=0
        # SLS reads exactly the installed source, never executes it, and refuses
        # edits to immutable dependency files even when referenced by a caller.
        client=Cliente([str(SF),'-P',str(ROOT/'ferramentas/sls/sls.fé')],project)
        try:
            client.inicie()
            text='local E=importe "exemplo"; mostre(E.somar(2,3))'
            uri=client.abra(text)
            params=client.no_ponto(uri,text,'somar',dentro=1)
            location=client.solicite('textDocument/definition',params)
            assert location and '/.santafe/geracoes/' in location['uri'],location
            response=client.solicite_bruto('textDocument/rename',{**params,'newName':'nova'})
            assert 'error' in response,response
        finally:
            client.feche()
        sf(f'garanta(C.instale({lit(project)},nulo,nulo,{{repositórioLocal={lit(repo)},semRede=verdadeiro}}))')
        assert (project/'santafe.lock').read_bytes()==lock
        offline_repo=tmp/'repo-desligado'; repo.rename(offline_repo)
        sf(f'garanta(C.instale({lit(project)},nulo,nulo,{{repositórioLocal={lit(repo)},semRede=verdadeiro}}))')
        offline_repo.rename(repo)
        # Immutable versions must not be replaced, even by the publisher.
        (src/'bibf/exemplo.fé').write_text('retorne {valor=43}\n')
        sf(f'local b=garanta(A.empacote({lit(src)})); garanta(A.adicione({lit(repo)},b))',success=False)
        assert initial==(repo/'indice.json').read_bytes()
        # Upgrade to genuinely different bytes, interrupted at each boundary.
        newer=tmp/'versao-nova'; fixture(newer,version='1.1.0')
        (newer/'bibf/exemplo.fé').write_text('retorne {valor=99}\n')
        sf(f'local b=garanta(A.empacote({lit(newer)})); garanta(A.adicione({lit(repo)},b))')
        for phase in ['verificado','preparado','transacao','manifesto','lock','confirmado']:
            upgrade=tmp/('atualizacao-'+phase); upgrade.mkdir()
            sf(f'garanta(C.instale({lit(upgrade)},"exemplo","1.0.0",{{repositórioLocal={lit(repo)}}}))')
            before=(upgrade/'santafe.lock').read_bytes()
            sf(f'garanta(C.instale({lit(upgrade)},"exemplo","1.1.0",{{repositórioLocal={lit(repo)},observador=função(f) se f=="{phase}" então erro("interrupção") fim fim}}))',success=False)
            expected=99 if phase=='confirmado' else 42
            def check_runtime():
                proc=subprocess.run([str(SF),'-e',f'garanta((importe "exemplo").valor=={expected})'],cwd=upgrade,env=ENV,capture_output=True,text=True)
                assert proc.returncode==0,proc.stderr
            check_runtime()
            sf(f'local r=garanta(N.raiz({lit(upgrade)})); garanta(r:trave()); C.recupere(r); r:feche()')
            check_runtime()
            assert ((upgrade/'santafe.lock').read_bytes()==before)==(phase!='confirmado')
            assert not (upgrade/'.santafe/transacao.json').exists()
        saved=(project/'santafe.lock').read_bytes()
        damaged=json.loads(saved); damaged['dependencias']['exemplo']='9.0.0'
        (project/'santafe.lock').write_text(json.dumps(damaged))
        sf(f'garanta(C.instale({lit(project)},nulo,nulo,{{repositórioLocal={lit(repo)},travado=verdadeiro}}))',success=False)
        (project/'santafe.lock').write_bytes(saved)
        # Recover interruptions at every journal/commit boundary.
        for phase in ['verificado','preparado','transacao','manifesto','lock','confirmado']:
            before=(project/'santafe.lock').read_bytes()
            sf(f'garanta(C.instale({lit(project)},nulo,nulo,{{repositórioLocal={lit(repo)},semRede=verdadeiro,observador=função(f) se f=="{phase}" então erro("interrupção simulada") fim fim}}))',success=False)
            sf(f'local r=garanta(N.raiz({lit(project)})); garanta(r:trave()); C.recupere(r); r:feche()')
            assert (project/'santafe.lock').read_bytes()==before
            assert not (project/'.santafe/transacao.json').exists()
        # First-install rollback must remove the newly created root mirrors;
        # after the state commit they must instead remain consistent.
        for phase in ['transacao','manifesto','lock','confirmado']:
            clean=tmp/('primeira-'+phase); clean.mkdir()
            sf(f'garanta(C.instale({lit(clean)},"exemplo","*",{{repositórioLocal={lit(repo)},observador=função(f) se f=="{phase}" então erro("interrupção") fim fim}}))',success=False)
            sf(f'local r=garanta(N.raiz({lit(clean)})); garanta(r:trave()); C.recupere(r); r:feche()')
            assert (clean/'santafe.json').exists()==(phase=='confirmado')
            assert (clean/'santafe.lock').exists()==(phase=='confirmado')
        # User edits after an interruption must not be overwritten by recovery.
        conflict=tmp/'conflito'; conflict.mkdir()
        sf(f'garanta(C.instale({lit(conflict)},"exemplo","*",{{repositórioLocal={lit(repo)},observador=função(f) se f=="manifesto" então erro("interrupção") fim fim}}))',success=False)
        (conflict/'santafe.json').write_text('{"mudanca":"usuario"}')
        sf(f'local r=garanta(N.raiz({lit(conflict)})); garanta(r:trave()); C.recupere(r)',success=False)
        assert (conflict/'santafe.json').read_text()=='{"mudanca":"usuario"}'
        # A forged cache object is never silently reused/downloaded over.
        cache=next((project/'.santafe/cache').glob('*.sfp')); original=cache.read_bytes(); cache.write_bytes(b'bad')
        sf(f'garanta(C.instale({lit(project)},nulo,nulo,{{repositórioLocal={lit(repo)},semRede=verdadeiro}}))',success=False)
        cache.write_bytes(original)
        for path in ['../escape','/tmp/escape','a/../../b','a//b','a/./b','x\\y']:
            sf(f'N.chaveCaminho({lit(path)})',success=False)
        outside=tmp/'outside'; outside.mkdir(); (outside/'secret').write_text('do not touch')
        (project/'link').symlink_to(outside, target_is_directory=True)
        sf(f'local r=garanta(N.raiz({lit(project)})); garanta(r:leia("link/secret"))',success=False)
        sf(f'local r=garanta(N.raiz({lit(project)})); garanta(r:grave("link/secret","changed",verdadeiro))',success=False)
        assert (outside/'secret').read_text()=='do not touch'
        os.mkfifo(project/'fifo')
        sf(f'local r=garanta(N.raiz({lit(project)})); garanta(r:leia("fifo"))',success=False)
        sf(f'local a=garanta(N.raiz({lit(project)})); local b=garanta(N.raiz({lit(project)})); garanta(a:trave()); garanta(b:trave())',success=False)
        # Package path/type/hash mutations are all rejected before writes.
        package=json.loads(original)
        for path in ['../escape','/escape','.ssh/key','A','a/b']:
            mutated=json.loads(original)
            mutated['arquivos'][0]['caminho']=path
            file=tmp/'bad.sfp'; file.write_text(json.dumps(mutated,ensure_ascii=False))
            sf(f'local r=garanta(N.raiz({lit(tmp)})); F.pacote(garanta(r:leia("bad.sfp")))',success=False)
        # Native package: refused by default; compiled only with explicit flag.
        native=tmp/'native'; fixture(native,name='nativo',native=True)
        sf(f'local b=garanta(A.empacote({lit(native)})); garanta(A.adicione({lit(repo)},b))')
        nproject=tmp/'native project'; nproject.mkdir()
        sf(f'garanta(C.instale({lit(nproject)},"nativo","*",{options}))',success=False)
        sf(f'garanta(C.instale({lit(nproject)},"nativo","*",{{repositórioLocal={lit(repo)},permitaNativo=verdadeiro,cabeçalhos={lit(ROOT/"src")}}}))')
        ns=json.loads((nproject/'.santafe/estado.json').read_text()); ng=nproject/'.santafe/geracoes'/ns['geracao']
        so=ng/'pacotes/nativo/nativo-soma.so'
        sf(f'local soma=garanta(módulo.carregarBib({lit(so)},"luaopen_soma"))(); garanta(soma(2,3)==5)')
        runtime=subprocess.run([str(SF),'-e','garanta((importe "soma")(2,3)==5)'],cwd=nproject,env=ENV,capture_output=True,text=True)
        assert runtime.returncode==0,runtime.stderr
        # No shell and no inherited credentials in compiler/download process.
        sf(f'local r=garanta(N.raiz({lit(project)})); local c,s=r:execute({{"/usr/bin/printf","%s","$(touch NEVER)"}},2); garanta(c==0 e s=="$(touch NEVER)")')
        sf(f'local r=garanta(N.raiz({lit(project)})); local c,s=r:execute({{"/usr/bin/env"}},2); garanta(c==0 e não s:procure("HOME="))')
        sf(f'local r=garanta(N.raiz({lit(project)})); local c=r:execute({{"/bin/sleep","2"}},1); garanta(c==124)')
        print('Pacotes: empacotamento determinístico, publicação imutável, instalação, offline, recuperação em 6 fases, confinamento, trava e módulo C: ok')

if __name__=='__main__': run()
