"""Prepara a bateria MSI21 sem modificar os critérios e fontes selados20."""
from pathlib import Path
import hashlib
import json
import shutil

repo = Path(__file__).resolve().parent.parent
dest = repo / 'apoio21'
assert dest.is_dir(), 'execute preparar-bateria.py primeiro'

def replace(name, pairs):
    p = dest / name
    text = p.read_text(encoding='utf-8')
    for old, new in pairs:
        assert old in text, (name, old)
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')

replace('msi.py', [("'dados.20' if version=='3.0.20'", "'dados.21' if version=='3.0.21'")])
replace('testar-instalador.py', [
    ("'dados.20'", "'dados.21'"),
    ('santafe-dados20-windows-x64', 'santafe-dados21-windows-x64'),
    ("bad=msi.build(portable,'3.0.21'", "bad=msi.build(portable,'3.0.22'"),
    ("new=msi.build(portable,'3.0.20'", "new=msi.build(portable,'3.0.21'"),
    ('fixture-falha21.msi', 'fixture-falha22.msi'),
    ('atualizar-16-para-20', 'atualizar-16-para-21'),
    ('instalacao20-integridade', 'instalacao21-integridade'),
    ('recusa-preservou20', 'recusa-preservou21'),
    ('desinstalar20', 'desinstalar21'),
])

# Preserva o controle positivo legado16 e acrescenta a atualização direta20→21.
base = repo / 'dados21/base'
meta = json.loads((base / 'dados20.json').read_text(encoding='utf-8'))
assert meta['sha256'] == 'c2be555fe471606a95107430c96be0d091690faa54bdc0c6c75de8c6ab441756'
assert hashlib.sha256((base / 'dados20.msi').read_bytes()).hexdigest() == meta['sha256']
shutil.copytree(base, dest / 'base21')
p = dest / 'testar-instalador.py'
s = p.read_text(encoding='utf-8')
anchor = " assert machinepath()==machine_before;ok('path-da-maquina-inalterado')"
assert s.count(anchor) == 1
extra = ''' # Pacote20 original conferido; falha sintética22 deve restaurá-lo.
 baseline20=HERE/'base21/dados20.msi'
 meta20=json.loads((HERE/'base21/dados20.json').read_text(encoding='utf-8'))
 assert digest(baseline20)==meta20['sha256']=='c2be555fe471606a95107430c96be0d091690faa54bdc0c6c75de8c6ab441756'
 metas.append(meta20)
 install('instalar-baseline20',['/i',baseline20,'INSTALLDIR='+str(target)])
 checkfiles(meta20,target,'baseline20-integridade')
 extra.write_text('nao excluir',encoding='utf-8')
 install('falha-atualizacao20-para22',['/i',badmsi],1603,'DADOS20_FALHA_APOS_COPIA_CONFIRMADA')
 checkfiles(meta20,target,'reversao-transacional-preservou20')
 assert state(meta20['product_code'])==5 and extra.read_text()=='nao excluir'
 install('atualizar20-para21',['/i',newmsi])
 checkfiles(new,target,'atualizacao20-21-integridade')
 assert state(meta20['product_code'])==-1 and state(new['product_code'])==5
 assert regpath()[0].lower().count(entry.lower())==1
 install('remover21-para-reverter20',['/x',new['product_code']])
 assert extra.read_text()=='nao excluir'
 # Apenas arquivo de ensaio dentro da pasta exclusiva criada por este roteiro.
 extra.unlink()
 install('reversao-deliberada-para20',['/i',baseline20,'INSTALLDIR='+str(target)])
 checkfiles(meta20,target,'reversao-deliberada20-integridade')
 install('remover20-apos-reversao',['/x',meta20['product_code']])
 assert state(meta20['product_code'])==-1 and state(new['product_code'])==-1
 assert {p.relative_to(workspace).as_posix():digest(p) for p in workspace.rglob('*') if p.is_file()}==project_hashes
 ok('ciclo20-21-20-preservou-projeto')
'''
p.write_text(s.replace(anchor, extra + anchor), encoding='utf-8')

replace('usuario-padrao.ps1', [('santafe-dados20-windows-x64', 'santafe-dados21-windows-x64')])
replace('validar-msi.py', [("'candidato':'dados.20'", "'candidato':'dados.21'")])
replace('testar-assinatura.ps1', [
    ('dados.20', 'dados.21'), ('santafe-dados20-windows-x64', 'santafe-dados21-windows-x64'),
    ('3.0.20.0', '3.0.21.0')])
replace('preparar-windows11.py', [
    ('santafe-dados20-windows-x64', 'santafe-dados21-windows-x64'),
    ('dados20.msi', 'dados21.msi'), ('dados20.json', 'dados21.json')])
replace('testar-windows11.py', [
    ('dados.20', 'dados.21'), ('dados20.msi', 'dados21.msi'), ('dados20.json', 'dados21.json'),
    ('atualizar19-para20', 'atualizar19-para21'), ('candidato20-integro', 'candidato21-integro'),
    ('reparar20', 'reparar21'), ('remover20', 'remover21')])
# Esse caso mantém a comparação19 na arquitetura ARM; não a substitui por20.
shutil.copytree(repo / 'dados20/base', dest / 'base')
for name in ('msi.py', 'testar-instalador.py', 'preparar-windows11.py', 'testar-windows11.py'):
    compile((dest/name).read_text(encoding='utf-8'), str(dest/name), 'exec')
print('INSTALADOR21_PREPARADO legado16, ciclo20-21-20 e Windows11ARM19-21-19')
