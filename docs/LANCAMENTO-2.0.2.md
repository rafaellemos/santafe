# Santafé 2.0.2 — fechamento da linha 2.0

Data do fechamento: 19 de outubro de 2026 (America/Sao_Paulo).
Esta revisão consolida correções já auditadas; não acrescenta funcionalidades
da linguagem, novos comandos LSP ou apelidos de compatibilidade.

## Componentes

| Componente | Versão |
| --- | --- |
| Núcleo e distribuição | 2.0.2 |
| SLS | 0.1.1 |
| VS Code | 1.0.6 |
| Sublime Text | 1.0.13 |
| Segmentação Unicode | 17.0.0 |

A ABI C continua 503 e o diretório de bibliotecas continua `santafé/1.0`.
Esses identificadores não são a versão pública. `_VERSÃO` informa a linha
`Santafé 2.0`; `santafé -v` informa a revisão 2.0.2.

## Correções consolidadas

- Grafemas, precisão de índices, separador binário e protocolo do SLS conforme
  a [auditoria](AUDITORIA-2.0-20261017.md).
- Instalação com falhas explícitas, sem REPL acidental nem alteração de rede.
- Editores com 610 entradas da API, edição de blocos, diagnósticos, realce de
  `®` e `Ⓡ`, continuidade HTML/JS em concatenações e paleta suave opcional.
- TAR/ZIP incluem `vendor/vscode-oniguruma/release/onig.wasm` e licenças:
  antes, o filtro genérico de binários impedia reconstruir o VSIX a partir
  do pacote completo. O WebAssembly gerado do núcleo continua fora do fonte.
- Manual distingue recursos das extensões de funcionalidades ainda ausentes
  no SLS. Capturas de tela locais não integram o pacote público.

## Estado operacional

Na conferência de 19/10, os editores públicos já eram 1.0.6/1.0.13, mas
`/baixar` ainda oferecia 2.0.1, o núcleo instalado anunciava 1.0.0 e o
executor WebAssembly era anterior à auditoria. O fechamento prepara uma
publicação reversível; somente o sucesso do publicador confirma a instalação.
Não se reescrevem pacotes históricos nem etiquetas Git anteriores.

O publicador compila e testa em diretório temporário antes de alterar o
servidor. Publica downloads 2.0.2, manual e WebAssembly; instala o núcleo,
compilador e SLS correspondentes; preserva os pacotes já publicados dos
editores. O fonte completo fica em uma árvore versionada independente,
sem sobrepor adaptações na árvore-fonte operacional antiga.

Não migra bancos, não altera configurações empresariais, bibliotecas dos
serviços, credenciais nem aplicações empresariais. Em `/opt`, somente a página
do portal `sfdev.fé` recebe os links atualizados. Somente o portal é reiniciado
para atualizar a página `/baixar`. Serviços persistentes que já estavam
executando continuam com o processo anterior até uma manutenção própria;
a instalação não deve ser descrita como atualização de todos os processos.

O executor novo fica em `/estático/wasm/2.0.2/`. Os arquivos antigos são
preservados para abas que ainda tenham JavaScript em cache. Uma falha na
publicação restaura os arquivos anteriores a partir da cópia privada.

Para publicar, após conferir os três arquivos em `/tmp`:

```sh
sudo bash /tmp/publicar-fechamento-santafe-2.0.2-v2.sh
```

O mesmo lançador aceita `--preflight` sem sudo para repetir a compilação e
as verificações em diretório temporário, sem instalar nem reiniciar serviços.

### Revisão 2 do fechamento

A primeira tentativa com `sudo` parou antes da instalação: fixtures com nomes
fixos em `/tmp` pertenciam a `rafael`, e `fs.protected_regular=2` impediu sua
reabertura por root. A revisão 2 usa diretórios privados criados atomicamente
para os ensaios de imagem, RPDF e Pulso, com limpeza após sucesso ou falha e
regressão concorrente. Não desativa a proteção do Linux nem remove fixtures
históricas. Núcleo, ABI, SLS e editores mantêm suas versões e implementações.

O registro original `v2.0.2` permanece intacto; `v2.0.2-r2` identifica os fontes
com essa correção de testes/publicação. Os pacotes 2.0.2 ainda não haviam sido
publicados no portal; o lançador novo fixa suas novas somas SHA-256. A guarda
de imutabilidade continua recusando trocar um arquivo público já existente
com conteúdo diferente.

## Homologação e limites

- O primeiro GitHub Actions de `v2.0.2-r2` compilou em Ubuntu 24.04 e macOS
  14, mas interrompeu a suíte HTTP por uma expectativa de horário fixa em
  Brasília. Os runners estavam em UTC. A correção posterior constrói a data
  da fixture no fuso local e repete o ensaio em UTC, America/Sao_Paulo e
  Asia/Tokyo, sem modificar o relógio nem o comportamento do Carteiro.
  A etiqueta e os downloads já publicados da revisão 2 permanecem intactos;
  os resultados do CI devem sempre ser associados ao commit efetivamente
  testado, sem atribuir aprovação retroativa à execução anterior.
- Núcleo/bibliotecas: suítes macOS Intel e Debian com MariaDB isolado.
- Editores: testes reais de VS Code e Sublime em macOS Intel, incluindo
  gabaritos, HTML/JS e reversibilidade da paleta suave.
- A instalação em prefixo isolado é testada com as dependências disponíveis.
  Isso não comprova o provisionamento completo de uma máquina vazia.
- Windows e Apple Silicon não recebem selo de homologação neste fechamento.
  CI nesses ambientes só pode ser declarado aprovado após execução observada.
- SLS: diagnóstico sintático local. Sem análise semântica entre arquivos,
  depurador ou gerenciador de bibliotecas.
- Pão do Café é uma implantação independente, não parte da plataforma.

## Reproduzir

Use os comandos no fim da auditoria. Gere o pacote com `make dist`, valide-o
com `testes/integracao/testar_distribuicao.py` e teste também a árvore extraída.
As somas em `SHA256SUMS` identificam os artefatos; os números de versão das
extensões não devem ser alterados ao reconstruir pacotes byte a byte iguais.
