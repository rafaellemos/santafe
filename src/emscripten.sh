#!/usr/bin/env bash
set -euo pipefail

# SantaFé 1.0 - compilação WebAssembly com Emscripten
# Execute este arquivo dentro da pasta fonte/src do SantaFé.
# O wasm.c deve estar nesta mesma pasta.

# O ambiente usado anteriormente no projeto era ~/emsdk.
if ! command -v emcc >/dev/null 2>&1; then
  if [ -f "$HOME/emsdk/emsdk_env.sh" ]; then
    # shellcheck disable=SC1090
    source "$HOME/emsdk/emsdk_env.sh"
  fi
fi

if ! command -v emcc >/dev/null 2>&1; then
  cat >&2 <<'MSG'
Emscripten (emcc) não encontrado.

Instalação usada no projeto:
  cd ~
  git clone https://github.com/emscripten-core/emsdk.git
  cd emsdk
  ./emsdk install latest
  ./emsdk activate latest
  source ./emsdk_env.sh

Depois volte à pasta fonte/src do SantaFé e execute novamente:
  ./emscripten.sh
MSG
  exit 1
fi

CORE=(
  lapi.c lcode.c lctype.c ldebug.c ldo.c ldump.c lfunc.c lgc.c llex.c
  lmem.c lobject.c lopcodes.c lparser.c lstate.c lstring.c ltable.c
  ltm.c lundump.c lvm.c lzio.c
)

LIBS=(
  lauxlib.c lbaselib.c lcorolib.c ldblib.c liolib.c lmathlib.c
  loslib.c lstrlib.c ltablib.c lutf8lib.c loadlib.c linit.c
)

ZLIB=(
  adler32.c compress.c crc32.c deflate.c infback.c inffast.c inflate.c
  inftrees.c trees.c uncompr.c zutil.c
)

# CJSON é compilado separadamente; linit.c apenas registra luaopen_cjson.
JSON=(lua_cjson.c strbuf.c fpconv.c)

# O empacotador do Emscripten não aceita acentos no nome do símbolo gerado
# para o caminho virtual. O carregador do Santafé também procura por .fe.
emcc \
  wasm.c \
  "${CORE[@]}" \
  "${LIBS[@]}" \
  "${ZLIB[@]}" \
  "${JSON[@]}" \
  -I. \
  -O2 \
  -DLUA_COMPAT_MAXN \
  -DLUA_COMPAT_MATHLIB \
  -D'lua_writestring(s,l)=sf_wasm_writestring(s,l)' \
  -D'lua_writeline()=sf_wasm_writeline()' \
  --no-entry \
  -s WASM=1 \
  -s ENVIRONMENT=web \
  -s ALLOW_MEMORY_GROWTH=1 \
  -s EXIT_RUNTIME=0 \
  -s FORCE_FILESYSTEM=1 \
  --embed-file ../bibs/bibf/bit32.fé@/bit32.fe \
  -s 'EXPORTED_FUNCTIONS=["_sf_init","_sf_run_code","_malloc","_free"]' \
  -s 'EXPORTED_RUNTIME_METHODS=["cwrap","ccall","UTF8ToString","stringToUTF8","lengthBytesUTF8","FS"]' \
  -o santafe.js \
  -lm

printf '\nGerados com sucesso:\n  santafe.js\n  santafe.wasm\n'
