#!/usr/bin/env bash
# Copia somente artefatos já compilados; falha na primeira cópia malsucedida.
set -euo pipefail
stage=${1:?etapa}; prefix=${2:?prefixo}; platform=${3:-linux}
[[ "$prefix" = /* && "$prefix" != / ]] || { echo 'Prefixo deve ser absoluto e diferente de /.' >&2; exit 2; }
case "$stage" in
  bin)
    install -d "$prefix/bin" "$prefix/include" "$prefix/lib"
    if [[ "$platform" == mingw ]]; then
      install -m 755 src/santafe.exe src/santafec.exe "$prefix/bin/"
    else
      install -m 755 src/santafé src/santafec "$prefix/bin/"
      install -m 755 ferramentas/sls/santafé-sls "$prefix/bin/"
    fi
    install -m 644 src/lua.h src/luaconf.h src/lauxlib.h src/lualib.h src/lua.hpp "$prefix/include/"
    install -m 644 src/liblua.a "$prefix/lib/"
    ;;
  sls)
    install -d "$prefix/share/santafé/1.0/ferramentas"
    install -m 644 ferramentas/sls/sls.fé "$prefix/share/santafé/1.0/ferramentas/"
    install -d "$prefix/share/santafé/1.0/ferramentas/sls"
    install -m 644 ferramentas/sls/analisador.fé ferramentas/sls/projetos.fé ferramentas/sls/semantica.fé ferramentas/sls/transporte.fé ferramentas/sls/api-publica.json "$prefix/share/santafé/1.0/ferramentas/sls/"
    if [[ "$platform" != mingw ]]; then
      install -m 755 ferramentas/sls/nativo.so "$prefix/share/santafé/1.0/ferramentas/sls/"
    fi
    ;;
  pacotes)
    if [[ "$platform" != mingw ]]; then
      install -d "$prefix/share/santafé/1.0/ferramentas/pacotes"
      for name in versoes resolvedor formatos cliente administracao ambiente cli; do
        install -m 644 "ferramentas/pacotes/$name.fé" "$prefix/share/santafé/1.0/ferramentas/pacotes/"
      done
      install -m 755 ferramentas/pacotes/nativo.so "$prefix/share/santafé/1.0/ferramentas/pacotes/"
    fi
    ;;
  c)
    install -d "$prefix/lib/santafé/1.0/bibc"
    suffix=so; [[ "$platform" != mingw ]] || suffix=dll
    for name in arquivo rede mariadb segredo tomada; do
      install -m 755 "bibs/bibc/$name/$name.$suffix" "$prefix/lib/santafé/1.0/bibc/"
    done
    ;;
  fe)
    while IFS= read -r -d '' file; do
      relative=${file#bibs/bibf/}
      target="$prefix/share/santafé/1.0/bibf/$relative"
      install -d "$(dirname "$target")"
      install -m 644 "$file" "$target"
    done < <(find bibs/bibf -type f \( -name '*.fé' -o -name '*.fé' -o -name '*.md' -o -name '*.ttf' -o -name 'OFL.txt' \) -print0)
    ;;
  pc)
    install -d "$prefix/lib/pkgconfig"
    {
      printf 'prefix=%s\n' "$prefix"
      printf '%s\n' 'exec_prefix=${prefix}' 'libdir=${exec_prefix}/lib' 'includedir=${prefix}/include' ''
      printf '%s\n' 'Name: Santafe' 'Description: Santafé (ramificação de Lua 5.3)'
      printf 'Version: %s\n' "${4:?versão}"
      printf '%s\n' 'Libs: -L${libdir} -llua' 'Libs.private: -lm' 'Cflags: -I${includedir}'
    } > "$prefix/lib/pkgconfig/santafe.pc"
    ;;
  *) echo 'Etapa desconhecida.' >&2; exit 2 ;;
esac
