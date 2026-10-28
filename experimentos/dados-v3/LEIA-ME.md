# Santafé candidato dados.3

Laboratório de listas, nulo armazenável, ONFÉ e migração das bibliotecas.
Não é uma versão estável nem um instalador. Não substituir executáveis,
serviços, bibliotecas C, catálogos ou dados em produção.

## Experimentar

Extraia o pacote de fontes em um diretório novo e entre nele. No macOS Intel
ou Debian x86-64, com as dependências de compilação já disponíveis:

```sh
python3 experimentos/dados-v3/conferir-fontes.py
sh experimentos/dados-v3/construir.sh
sh experimentos/dados-v3/experimentar.sh exemplo
sh experimentos/dados-v3/experimentar.sh testes
```

Não há `sudo`, instalação de dependências automática ou cópia para `/usr`.
Os módulos C precisam de compilador, `make`, `pkg-config`, GLib/GIO, MariaDB
Connector, libsodium e OpenSSL; no macOS também é usado CommonCrypto do sistema.
O arquivo `MIGRACAO.json` registra a transformação explícita aplicada às fontes.
O manifesto SHA-256 confere arquivos, mas não substitui a autenticidade do
canal por onde o pacote foi recebido.

O exemplo demonstra `[]`, `nulo`, `tabela.temChave`, `tabela.apague`, ONFÉ e
colares brutos. Um `\n` literal é representado como `\\n` no texto JSON e volta
a ser barra invertida seguida de `n` ao decodificar. Quebras reais são distintas.

O comando `sh experimentos/dados-v3/experimentar.sh sls` inicia o LSP do
laboratório por stdin/stdout. Não altera a configuração dos editores.

## Repetir os testes de integração

```sh
python3 experimentos/dados-v3/testar-bibliotecas.py
python3 experimentos/dados-v3/testar-abi.py
python3 experimentos/dados-v3/testar-mariadb.py
```

O primeiro comando separa 11 testes que exigem banco; o último executa esses
11 e mais um ensaio de SQL NULL em uma instância MariaDB temporária própria.
Requer `mariadbd`, `mariadb-install-db` e `mariadb` previamente disponíveis.
Usa `--no-defaults`, socket privado, loopback e credenciais fictícias. Não usa
os arquivos de configuração nem as contas do banco instalado. O servidor
temporário é encerrado ao final; os dados fictícios e logs são preservados
no caminho informado. Os testes de rede exigem loopback liberado pelo ambiente.

Para WebAssembly, ative o Emscripten existente e use um cache gravável privado:

```sh
cd src
SANTAFE_EXPERIMENTO_DADOS=1 bash emscripten.sh
node ../experimentos/dados-v3/testar-wasm.js
```

Defina `EM_CACHE` se o cache da instalação for somente leitura. A bateria usa
Node com DOM mínimo e não equivale a uma inspeção visual do portal.

## Limites

Veja `RELATORIO.md`. Os fontes dos aplicativos presentes na árvore não são
uma declaração de migração/homologação integral desses aplicativos. O
gerenciador de pacotes, toda a distribuição, manual público e editores não
foram publicados ou instalados por esta rodada. Os artefatos dados.2 e a
instalação estável permanecem preservados.
