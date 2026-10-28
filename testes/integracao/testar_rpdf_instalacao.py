#!/usr/bin/env python3
"""RPDF deve usar a fonte vizinha ao módulo, sem depender do diretório atual."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BINARY = ROOT / 'src/santafé'

with tempfile.TemporaryDirectory(prefix='santafe-rpdf-') as temporary:
    root = Path(temporary)
    library = root / 'instalação isolada/share/santafé/3.0/bibf'
    font = library / 'rpdf/fontes/NotoSans-Regular.ttf'
    font.parent.mkdir(parents=True)
    shutil.copy2(ROOT / 'bibs/bibf/rpdf_unicode.fé', library)
    shutil.copy2(ROOT / 'bibs/bibf/rpdf/fontes/NotoSans-Regular.ttf', font)
    working = root / 'outro diretório'
    working.mkdir()
    environment = dict(os.environ, LUA_PATH=f'{library}/?.fé')
    environment.pop('RPDF_FONTE', None)
    module_path = json.dumps(str(library / 'rpdf_unicode.fé'), ensure_ascii=False)

    def check(loader, expected, env):
        source = f'''local U = {loader}
local caminho = U.localizeFonte()
local fonte = U.carregueFonte(caminho)
garanta(fonte:glifo(233) > 0, "fonte sem glifo é")
mostre(caminho)'''
        result = subprocess.run([str(BINARY), '-e', source], cwd=working,
                                env=env, capture_output=True, text=True,
                                check=True, timeout=10)
        assert Path(result.stdout.strip()).resolve() == expected.resolve(), (
            f'{loader}: fonte fora da instalação: {result.stdout}')

    for loader in ('importe "rpdf_unicode"', f'executeArquivo({module_path})'):
        check(loader, font, environment)
    # O caminho fornecido pelo carregador deve bastar sem a biblioteca depure.
    check('(função() depure = nulo; retorne importe "rpdf_unicode" fim)()',
          font, environment)
    # A escolha explícita do usuário continua tendo precedência.
    override = root / 'fonte escolhida.ttf'
    shutil.copy2(font, override)
    check('importe "rpdf_unicode"', override,
          dict(environment, RPDF_FONTE=str(override)))

print('RPDF: fonte no prefixo isolado, importe/executeArquivo e RPDF_FONTE: ok')
