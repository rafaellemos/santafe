#!/usr/bin/env python3
"""Nova árvore, derivada do pacote dados.5 conferido. Nunca escreve produção."""
from pathlib import Path
import hashlib, shutil, subprocess, tarfile, tempfile
ROOT=Path(__file__).resolve().parents[2]
archive=ROOT/'dist/candidato-dados-v5/santafe-candidato-dados.5-fontes.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='8b096db59c22939bdfb306a573ff01b9e6758e70683d7c2f7e94833378bb854f'
stage=Path(tempfile.mkdtemp(prefix='santafe-dados6-',dir='/tmp'))
with tarfile.open(archive) as package:
    for m in package.getmembers():
        assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
    package.extractall(stage)
subprocess.run(['python3',str(stage/'experimentos/dados-v3/conferir-fontes.py')],check=True)
shutil.copytree(ROOT/'experimentos/dados-v6',stage/'experimentos/dados-v6',ignore=shutil.ignore_patterns('__pycache__'))
for name in ('manual.html','validar-manual.py','API-PUBLICA-FE.tsv','CONTRATO-DADOS-ONFE.md',
             'PLANO-PUBLICACAO-CONJUNTA-20261021.md'):
    shutil.copy2(ROOT/'docs'/name,stage/'docs'/name)
p=stage/'docs/CONTRATO-DADOS-ONFE.md'
t=p.read_text().replace('O construtor isolado não habilita carregamento dinâmico de módulos.',
    'Desde dados.3, o laboratório carrega módulos C recompilados com a ABI experimental. Não reutilize módulos estáveis; o marcador de versão não protege módulos que omitem a checagem de ABI.')
t=t.replace('O candidato `dados.2` integra', 'O candidato atual `dados.6` integra')
t=t.replace('no candidato `dados.2`, o serviço completo', 'no candidato, o serviço completo')
t+='\n\nEstado de homologação atualizado: consulte experimentos/dados-v6/RELATORIO.md. Os resultados históricos de dados.2 não substituem os gates pendentes atuais.\n'
p.write_text(t)
for name,old,new in [('src/lua.h','"dados.5"','"dados.6"'),
                     ('ferramentas/sls/sls.fé','1.0.0-dados.5','1.0.0-dados.6')]:
    p=stage/name; t=p.read_text(); assert t.count(old)==1; p.write_text(t.replace(old,new))
# Testes de instalação herdados agora conferem a identidade da geração 6.
p=stage/'experimentos/dados-v5/testar-instalacao.py'
t=p.read_text().replace('dados.5','dados.6'); p.write_text(t)
for name in ('Makefile','instalar.sh','experimentos/dados-v3/testar-wasm.js'):
    p=stage/name; p.write_text(p.read_text().replace('dados.5','dados.6'))
(stage/'.laboratorio-dados6').write_text('candidato isolado; não instalar em produção\n')
# Carga usa os mesmos serviços reais e suas credenciais exclusivamente sintéticas.
p=stage/'experimentos/dados-v5/testar-aplicativos.py'; t=p.read_text()
anchor="        for path in lab.path.glob('*.pulso'):"
assert t.count(anchor)==1
t=t.replace(anchor,"        import runpy\n        carga=runpy.run_path(str(ROOT/'experimentos/dados-v6/carga.py'))\n        carga['execute'](lab,ports,http,context,password,dns)\n"+anchor)
p.write_text(t)
subprocess.run(['python3',str(stage/'experimentos/dados-v6/aplicar.py')],check=True)
subprocess.run(['python3',str(stage/'experimentos/dados-v6/manual.py'),str(ROOT/'src/santafé')],check=True)
print(stage)
