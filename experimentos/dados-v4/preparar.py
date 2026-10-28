#!/usr/bin/env python3
"""Estende o candidato dados.3 somente em uma árvore de laboratório nova."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
archive = ROOT/'dist/candidato-dados-v3/santafe-candidato-dados.3-fontes.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '94712e586d29b956b3cc6aa99250d330be260b529d598dd86f5be5bb28b80008'
stage = Path(tempfile.mkdtemp(prefix='santafe-dados4-', dir='/tmp'))
with tarfile.open(archive) as package:
    for m in package.getmembers():
        assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts, m.name
    package.extractall(stage)
subprocess.run(['python3',str(stage/'experimentos/dados-v3/conferir-fontes.py')], check=True)
report = []
def change(name, before, after, count=1):
    file=stage/name; text=file.read_text()
    assert text.count(before)==count,(name,before,text.count(before),count)
    file.write_text(text.replace(before,after))
    report.append(dict(arquivo=name,antes=before,depois=after,ocorrencias=count))

for name in ('ferramentas/pacotes/nativo.c', 'src/lua_cjson.c', 'operação/preparar-catalogo-bibliotecas.py', 'LICENSE'):
    path=stage/name; path.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/name,path)
name='extensões/testes/identificadores-unicode.json'
path=stage/name; path.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/name,path)
shutil.copytree(ROOT/'bibliotecas',stage/'bibliotecas')
shutil.copytree(ROOT/'experimentos/dados-v4',stage/'experimentos/dados-v4',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
# CLI ficou fora da migração léxica das bibliotecas no candidato anterior.
cli=stage/'ferramentas/pacotes/cli.fé'
p=subprocess.run([str(ROOT/'dist/candidato-dados-v2-baseline/santafé-dados'),'-E','-P',
                  str(ROOT/'experimentos/dados-v1/migrar.fé'),str(cli)],capture_output=True,check=True)
cli.write_bytes(p.stdout)

change('src/lua.h','#define SANTAFE_DADOS_VERSION "dados.3"','#define SANTAFE_DADOS_VERSION "dados.4"')
change('ferramentas/sls/sls.fé','1.0.0-dados.3','1.0.0-dados.4')
change('experimentos/dados-v3/testar-wasm.js', 'const deadline=setTimeout',
       'cases.push(fs.readFileSync(path.join(root,"experimentos/dados-v4/testar-colares.fé"),"utf8").replace("experimentos/dados-v1/onfé.fé","/onfé.fé"));\nconst deadline=setTimeout')
change('experimentos/dados-v3/testar-wasm.js', 'WebAssembly dados.3:', 'WebAssembly dados.4:')
change('ferramentas/pacotes/formatos.fé','exija(tipo(t)=="tabela",descrição..": lista esperada")',
       'exija(tipo(t)=="lista",descrição..": lista esperada")')
# O codificador canônico não adivinha arrays pelo primeiro índice da tabela.
name='ferramentas/pacotes/formatos.fé'
text=(stage/name).read_text()
start=text.index('    função F.canônico(dados)')
end=text.index('    função F.hash(h)',start)
replacement=(ROOT/'experimentos/dados-v4/canonico.fé').read_text()
change(name,text[start:end],replacement)
for before,after in [('local arquivos={}','local arquivos=[]'),('local caminhos={}','local caminhos=[]')]:
    change('ferramentas/pacotes/administracao.fé',before,after)
change('ferramentas/pacotes/resolvedor.fé','visitando[nome]=nulo','tabela.apague(visitando,nome)')
change('ferramentas/pacotes/resolvedor.fé','seleção[próximo]=nulo','tabela.apague(seleção,próximo)')
change('ferramentas/pacotes/cliente.fé','local transação={formato=1,geracao=geração,arquivos={',
       'local transação={formato=1,geracao=geração,arquivos=[')
change('ferramentas/pacotes/cliente.fé','depois=N.base64(lockBruto)}}}', 'depois=N.base64(lockBruto)}]}')
# Suporte C informa a ABI experimental e receitas autorizadas compilam para ela.
change('ferramentas/pacotes/cliente.fé','                    se plataforma.sistema=="Darwin" então',
       '                    se plataforma.abiDados então argumentos[#argumentos+1]="-DSANTAFE_DADOS_EXPERIMENTAL" fim\n                    se plataforma.sistema=="Darwin" então')
# A fixture passa a detectar de verdade uma receita compilada com ABI antiga.
change('testes/integracao/testar_pacotes.py','int luaopen_soma(lua_State*L){lua_pushcfunction(L,f);',
       'int luaopen_soma(lua_State*L){luaL_checkversion(L);lua_pushcfunction(L,f);')
# Não permitir herdar caminhos/credenciais nem importar módulos instalados.
change('testes/integracao/testar_pacotes.py',"ENV = {**os.environ, 'LUA_PATH': str(ROOT / 'ferramentas/?.fé')+';;'}",
       "ENV = {k:os.environ[k] for k in ('PATH','TMPDIR','LANG','LC_ALL') if k in os.environ}\nENV.update(LUA_PATH=str(ROOT/'ferramentas/?.fé'), LUA_CPATH=str(ROOT/'ferramentas/?/?.so'),GSETTINGS_BACKEND='memory')")
# Falhas de memória: o harness C usa cabeçalhos compatíveis com o binário.
change('testes/integracao/testar_pacotes_memoria.py',"command+=['-ldl']","command+=['-ldl','-lcrypto']")
change('testes/integracao/testar_sls_memoria.py',"command+=['-ldl']","command+=['-ldl','-lcrypto']")
change('testes/integracao/sls/lexemas_memoria.c','assert(lua_istable(L,1));','assert(lua_islist(L,1));')
(stage/'MIGRACAO-CADEIA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(stage/'.laboratorio-dados4').write_text('somente laboratório; dados.3 preservado\n')
print(stage)
