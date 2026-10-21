#!/usr/bin/env bash
# Remove apenas os arquivos conhecidos desta distribuição, nunca diretórios.
set -euo pipefail
stage=${1:?etapa}; prefix=${2:?prefixo}; platform=${3:-linux}
[[ "$prefix" = /* && "$prefix" != / ]] || { echo 'Prefixo deve ser absoluto e diferente de /.' >&2; exit 2; }
remove_file() { rm -f -- "$prefix/$1"; }
case "$stage" in
  bin)
    if [[ "$platform" == mingw ]]; then
      remove_file bin/santafe.exe; remove_file bin/santafec.exe
    else
      remove_file bin/santafé; remove_file bin/santafec; remove_file bin/santafé-sls
    fi
    for name in lua.h luaconf.h lauxlib.h lualib.h lua.hpp; do remove_file "include/$name"; done
    remove_file lib/liblua.a
    remove_file share/santafé/1.0/ferramentas/sls.fé
    for name in analisador.fé projetos.fé semantica.fé transporte.fé api-publica.json nativo.so; do
      remove_file "share/santafé/1.0/ferramentas/sls/$name"
    done
    for name in versoes.fé resolvedor.fé formatos.fé cliente.fé administracao.fé ambiente.fé cli.fé nativo.so; do
      remove_file "share/santafé/1.0/ferramentas/pacotes/$name"
    done
    ;;
  bibs)
    suffix=so; [[ "$platform" != mingw ]] || suffix=dll
    for name in arquivo rede mariadb segredo tomada; do remove_file "lib/santafé/1.0/bibc/$name.$suffix"; done
    while IFS= read -r -d '' file; do
      remove_file "share/santafé/1.0/bibf/${file#bibs/bibf/}"
    done < <(find bibs/bibf -type f \( -name '*.fé' -o -name '*.fé' -o -name '*.md' -o -name '*.ttf' -o -name 'OFL.txt' \) -print0)
    remove_file lib/pkgconfig/santafe.pc
    ;;
  *) echo 'Etapa desconhecida.' >&2; exit 2 ;;
esac
