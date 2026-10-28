# Laboratório Santafé dados.4

Continuação de dados.3: gerenciador de bibliotecas migrado e testes ampliados.
Não é a próxima versão estável nem um instalador. Use somente uma extração
nova em diretório descartável; não sobreponha o fonte/instalação de produção.

## Compilar e repetir a bateria

No macOS Intel ou Debian x86-64, com compilador, make, pkg-config, Python 3,
GLib/GIO, MariaDB Connector, libsodium, OpenSSL e curl já disponíveis:

```sh
python3 experimentos/dados-v3/conferir-fontes.py
sh experimentos/dados-v3/construir.sh
make -C ferramentas/pacotes CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
python3 experimentos/dados-v4/testar-cadeia.py
python3 experimentos/dados-v3/testar-bibliotecas.py
python3 experimentos/dados-v3/testar-abi.py
sh experimentos/dados-v3/experimentar.sh testes
./src/santafé -E -P experimentos/dados-v4/testar-colares.fé
```

As referências dados-v3 são harnesses reutilizados, não uma seleção de binário
antigo. `src/santafé` desta árvore deve identificar o candidato dados.4.
`MIGRACAO.json` e `MIGRACAO-CADEIA.json` registram as transformações.

O grupo HTTPS usa um servidor loopback e uma CA descartável; o catálogo é
local. Não há instalação global, envio postal, atualização de catálogo público
ou uso de credenciais reais. Logs ficam em `evidencias/`.

Com `mariadbd`, `mariadb-install-db` e `mariadb` disponíveis, execute também:

```sh
python3 experimentos/dados-v3/testar-mariadb.py
```

Esse comando cria e encerra uma instância privada, sem configurações do banco
instalado. Os 11 testes separados por falta de banco na bateria geral só são
aprovados quando esta etapa passa. Não usar `sudo`.

Para SLS (sem alterar os editores):

```sh
SANTAFE_CANDIDATO="$PWD/src/santafé" SANTAFE_ESTAVEL="$PWD/src/santafé" python3 experimentos/dados-v2/testar-sls.py
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 --comando /bin/sh "$PWD/experimentos/dados-v3/santafe-sls-dados"
```

Nessa bateria SLS, a variável de ambiente com nome ESTAVEL seleciona o
interpretador do corpus adaptado; não afirma que o candidato é estável.
As comparações reais contra o núcleo estável são uma bateria separada.

Para WebAssembly, ative o Emscripten existente e um `EM_CACHE` privado gravável,
entre em `src`, execute `SANTAFE_EXPERIMENTO_DADOS=1 bash emscripten.sh` e depois
`node ../experimentos/dados-v3/testar-wasm.js`. Não substituir arquivos do portal.

Veja `RELATORIO.md` para resultados efetivamente executados e pendências.
