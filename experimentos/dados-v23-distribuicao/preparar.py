#!/usr/bin/env python3
"""Prepara a distribuição IBA3 padrão em cópia nova. Não instala nem publica."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

BASE = 'd1ab79a6024e12cf9c571af929b099531d71776e898bf406844b23ea00128be9'
HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def preparar(archive, destination):
    if sha(archive.read_bytes()) != BASE:
        raise ValueError('Fonte dados.22 não confere')
    if destination.exists() or destination.is_symlink():
        raise ValueError('Exige destino novo')
    files = {}
    with tarfile.open(archive) as package:
        for item in package:
            rel = PurePosixPath(item.name)
            if (not item.isfile() or rel.is_absolute() or '..' in rel.parts
                    or str(rel) != item.name or item.name in files
                    or item.size > 32 * 1024**2):
                raise ValueError('Membro inseguro: ' + item.name)
            files[item.name] = (package.extractfile(item).read(), item.mode & 0o755)
    expected = json.loads(files['MANIFESTO-FONTES.json'][0])
    actual = {name: sha(data) for name, (data, _) in files.items()
              if name != 'MANIFESTO-FONTES.json'}
    if expected != actual or len(expected) != 887:
        raise ValueError('Manifesto de origem divergente')
    destination.mkdir(parents=True, mode=0o700)
    for name, (data, mode) in files.items():
        p = destination/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        p.chmod(mode)

    def edit(name, old, new, count=1):
        p = destination/name
        text = p.read_text()
        if text.count(old) != count:
            raise ValueError('Origem mudou: ' + name + ': ' + repr(old))
        p.write_text(text.replace(old, new))

    # O contrato é parte do SDK, não uma opção passada ao compilador. A
    # distribuição 3 não oferece combinação binária com a estrutura antiga.
    for folder in ('src', 'bibs', 'ferramentas'):
        for p in (destination/folder).rglob('*'):
            if p.suffix in ('.c', '.h', '.fé'):
                t = p.read_text()
                if 'SANTAFE_DADOS_EXPERIMENTAL' in t:
                    p.write_text(t.replace('SANTAFE_DADOS_EXPERIMENTAL', 'SANTAFE_DADOS_V3'))
    edit('src/luaconf.h', '#define luaconf_h', '''#define luaconf_h

/* Santafé 3: contrato de dados e IBA3 habilitados em todo consumidor do SDK. */
#if defined(SANTAFE_DADOS_V3) && SANTAFE_DADOS_V3 != 1
#error "A distribuicao Santafe 3 exige SANTAFE_DADOS_V3=1"
#endif
#define SANTAFE_DADOS_V3 1''')
    # Esta unidade não inclui lua.h, mas contém tratamento JSON específico.
    edit('src/fpconv.c', '#include "fpconv.h"', '#include "luaconf.h"\n#include "fpconv.h"')
    edit('src/lua.h', '#define SANTAFE_VERSION_MAJOR "2"', '#define SANTAFE_VERSION_MAJOR "3"')
    edit('src/lua.h', '#define SANTAFE_VERSION_MINOR "1"', '#define SANTAFE_VERSION_MINOR "0"')
    edit('src/lua.h', '''#ifdef SANTAFE_DADOS_V3
#undef LUA_RELEASE
#ifndef SANTAFE_DADOS_VERSION
#define SANTAFE_DADOS_VERSION "dados.22"
#endif
#define LUA_RELEASE "Santafé candidato-" SANTAFE_DADOS_VERSION " (experimental, não usar em produção)"
#endif''', '''#undef LUA_RELEASE
#define LUA_RELEASE "Santafé 3.0.0-rc.1 (homologação dados.23; não publicado)"''')
    edit('src/lua.h', '''** Os números acima preservam o layout de módulos e o formato binário 1.0.
** A versão pública é independente. LUA_VERSION_NUM permanece 503
** porque identifica a ABI C herdada do Lua 5.3; não significa
** compatibilidade da sintaxe ou do vocabulário público com Lua.''', '''** Os números LUA_VERSION_* são identificadores históricos da API.
** A IBA é SANTAFE_ABI_MAJOR=3, os módulos usam o diretório 3.0 e
** o bytecode usa SF3. LUA_VERSION_NUM=503 não autoriza carregar
** bibliotecas binárias Lua nem módulos Santafé de gerações anteriores.''')
    edit('src/luaconf.h', '#define LUA_VDIR\tLUA_VERSION_MAJOR "." LUA_VERSION_MINOR', '#define LUA_VDIR "3.0"')
    edit('src/santafe.c', '/1.0/ferramentas/pacotes', '/3.0/ferramentas/pacotes')
    edit('ferramentas/sls/sls.fé', 'Dados.experimental e "1.0.0-dados.22" ou "1.0.0"', '"1.1.0-rc.1"')
    edit('ferramentas/pacotes/cli.fé', 'Santafé Bibliotecas 1.0.0', 'Santafé Bibliotecas 1.1.0-rc.1')
    edit('ferramentas/pacotes/cli.fé', 'Disponível na distribuição Santafé 2.1.0;', 'Candidato da distribuição Santafé 3.0.0-rc.1;')
    edit('ferramentas/pacotes/cli.fé', 'candidato dados.22', 'candidato dados.23')
    for name in ('ferramentas/instalar-arquivos.sh', 'ferramentas/desinstalar-arquivos.sh',
                 'ferramentas/sls/santafé-sls'):
        p = destination/name
        p.write_text(p.read_text().replace('/santafé/1.0/', '/santafé/3.0/'))
    edit('ferramentas/sls/iniciador-windows.c', '/1.0/ferramentas/sls/', '/3.0/ferramentas/sls/')
    # Caminhos ativos de instalação e a fonte padrão do PDF seguem a IBA3.
    for p in [destination/'Makefile', destination/'bibs/bibf/rpdf_unicode.fé',
              *sorted((destination/'bibs/bibc').glob('*/Makefile'))]:
        p.write_text(p.read_text().replace('/santafé/1.0/', '/santafé/3.0/').replace('SFV = 1.0', 'SFV = 3.0'))
    edit('docs/manual.html', 'dados.22', 'dados.23', (destination/'docs/manual.html').read_text().count('dados.22'))
    edit('experimentos/dados-v3/testar-wasm.js', 'WebAssembly dados.22:', 'WebAssembly dados.23:')
    edit('Makefile', 'Candidato dados.22: use sh experimentos/dados-v3/construir.sh',
         'Candidato dados.23: use sh experimentos/dados-v23-distribuicao/construir.sh')
    edit('Makefile', 'VERSION := 2.1.0', 'VERSION := 3.0.0-rc.1')
    edit('instalar.sh', 'Candidato dados.22: use experimentos/dados-v3/construir.sh',
         'Candidato dados.23: use experimentos/dados-v23-distribuicao/construir.sh')
    edit('docs/manual.html', '#  Versao=2.0', '#  Versao=3.0.0-rc.1')
    edit('docs/manual.html', '<strong>Somente homologação.</strong>',
         '<strong>Somente homologação — 3.0.0-rc.1 (dados.23).</strong> '
         'O contrato de dados e a IBA3 são padrão; bibliotecas usam o diretório '
         '<code>santafé/3.0</code>. Este candidato inclui SLS e gerenciador '
         '<code>1.1.0-rc.1</code>. As referências abaixo à versão 2.1 descrevem '
         'a publicação anterior, não autorização para misturar as distribuições.')
    edit('ferramentas/instalar-arquivos.sh', '''      if [[ "$4" == *-dados.* ]]; then
        printf '%s\\n' 'Cflags: -I"${includedir}" -DSANTAFE_DADOS_EXPERIMENTAL'
      else
        printf '%s\\n' 'Cflags: -I"${includedir}"'
      fi''', '''      printf '%s\\n' 'Cflags: -I"${includedir}"' ''')
    edit('src/emscripten.sh', '''# Opt-in estritamente de laboratório; a construção pública não muda.
DADOS_FLAGS=()
if [ "${SANTAFE_EXPERIMENTO_DADOS:-0}" = 1 ]; then
  DADOS_FLAGS=(-DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK)
fi''', '''# O cabeçalho público habilita IBA3, inclusive no WebAssembly.
DADOS_FLAGS=(-DLUA_USE_APICHECK)''')
    # Atualiza as expectativas dos ensaios executados, sem afrouxar critérios.
    paths_active = {'experimentos/dados-v5/testar-instalacao.py',
                    'experimentos/dados-v6/operacao.py',
                    'experimentos/dados-v6/testar-operacao.py'}
    for folder in ('experimentos', 'testes'):
        for p in (destination/folder).rglob('*.py'):
            t = p.read_text()
            if folder == 'testes' or p.relative_to(destination).as_posix() in paths_active:
                t = t.replace('/santafé/1.0/', '/santafé/3.0/')
            t = t.replace('candidato-dados.22', '3.0.0-rc.1')
            t = t.replace('1.0.0-dados.22', '1.1.0-rc.1')
            if p.relative_to(destination).as_posix() == 'experimentos/dados-v5/testar-instalacao.py':
                t = t.replace('Candidato dados.22', 'Candidato dados.23')
            if folder == 'testes':
                t = t.replace('SANTAFE_DADOS_EXPERIMENTAL', 'SANTAFE_DADOS_V3')
            p.write_text(t)
    edit('experimentos/dados-v10/testar-iba.py', "assert '-DSANTAFE_DADOS_EXPERIMENTAL' in cflags", "assert not any(x.startswith('-DSANTAFE_DADOS') for x in cflags)")
    # A regressão IBA precisa provar que o SDK público basta para módulos C/C++.
    edit('experimentos/dados-v10/testar-iba.py', "'cc','-fPIC','-DSANTAFE_DADOS_EXPERIMENTAL',", "'cc','-fPIC',")
    # Os publicadores antigos permanecem bloqueados; só a cópia privada pode
    # ser montada nesta etapa. Não apontar usuários para o publicador 2.1.
    recipe = destination/'experimentos/dados-v23-distribuicao'
    recipe.mkdir()
    for p in HERE.iterdir():
        if p.is_file() and p.suffix in ('.py', '.md', '.sh'):
            (recipe/p.name).write_bytes(p.read_bytes())
    (destination/'.laboratorio-dados23').write_text('Distribuição isolada IBA3.\n')
    (destination/'IDENTIDADE.json').write_text(json.dumps({
        'nucleo': '3.0.0-rc.1', 'candidato': 'dados.23', 'iba': 3,
        'sls': '1.1.0-rc.1', 'bibliotecas': '1.1.0-rc.1',
        'diretorio_modulos': '3.0', 'base_sha256': BASE,
        'publicado': False, 'instalacao_global_habilitada': False,
    }, ensure_ascii=False, indent=2)+'\n')
    manifest = {str(p.relative_to(destination)): sha(p.read_bytes())
                for p in sorted(destination.rglob('*'))
                if p.is_file() and p.name != 'MANIFESTO-FONTES.json'}
    (destination/'MANIFESTO-FONTES.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print('DISTRIBUICAO23_PREPARADA', destination, len(manifest))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('destino', type=Path)
    args = parser.parse_args()
    preparar(args.base.resolve(), args.destino.absolute())
