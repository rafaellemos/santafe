# Auditoria da linha Santafé 2.0 — 17 de outubro de 2026

## Parecer

A mudança de versão maior **2.0 é justificada**, pois há alterações incompatíveis
no vocabulário e no comportamento público. Isso não equivale a confirmar que
todas as instalações já executam o mesmo artefato ou que não existem defeitos.

Esta auditoria corrigiu a árvore local e prepara a **candidata 2.0.2**, com
SLS 0.1.1, VS Code 1.0.1 e Sublime 1.0.8. Não republica nem altera os arquivos
históricos 2.0.0/2.0.1. As suítes em macOS e Debian passaram. A promoção e a
implantação desta candidata permanecem pendentes de revisão final nos editores
reais e da publicação operacional.

Escopo: mudanças recentes de vocabulário, grafemas, índices, compatibilidade,
SLS, extensões, instalação, distribuição, documentação e regressões disponíveis
do ecossistema. Não é uma certificação de segurança completa de todo o código
herdado ou um teste de carga prolongado de produção.

## Problemas encontrados e correções

| Área | Defeito ou inconsistência | Correção e evidência |
| --- | --- | --- |
| Versão | O núcleo ainda anunciava 1.0.0, enquanto o portal anunciava 2.0. | Macros de versão pública 2.0.2; testes nativo, instalado e WASM. A ABI 503 e o layout de bibliotecas 1.0 permanecem deliberadamente separados. |
| Grafemas | A tabela aproximada não implementava integralmente as propriedades e regras atuais adotadas. | Dados oficiais Unicode 17.0.0, propriedades GCB/EP/InCB e regra GB9c; 766 casos oficiais e 1.990 fronteiras verificadas. |
| Dados binários | `colar.junte` truncava separadores que continham NUL. | Uso do comprimento explícito do separador; regressão nativa e WASM. |
| Tabelas | `tabela.maiorÍndice` convertia chaves inteiras para ponto flutuante, perdendo precisão acima de 2^53. | Comparação numérica preservando o tipo; teste com 9007199254740993. |
| SLS | Ciclo de vida, cabeçalhos sem limite, requisições malformadas e versões antigas de documentos não tinham tratamento suficiente. | Limites de enquadramento, erros JSON-RPC, shutdown/exit, sincronização integral e descarte de versões antigas; testes com prazo máximo. |
| VS Code | Reinício podia esperar o identificador errado de initialize ou ser afetado por eventos do processo anterior. | Identificador dinâmico, isolamento dos processos e diagnósticos por versão. O servidor não é iniciado em workspace não confiável. |
| Catálogo | As extensões ofereciam sobretudo contratos Fé, omitindo APIs do núcleo/C. | Gerador compartilhado a partir dos mesmos contratos C/Fé conferidos pelo manual. |
| Sublime | Requisito Python restritivo, comentários/colares longos incompletos, nomes Unicode e fechamento de blocos. | Metadados Python 3.8/3.14, realce atualizado, conclusões aninhadas e fechamento sem duplicar `fim` imediatamente seguinte. |
| Execução no Sublime | O arquivo era inserido em um comando de shell; o PATH de aplicativos gráficos podia não encontrar o núcleo. | Argumentos separados e procura nos prefixos de instalação; ensaio com espaços e metacaracteres no nome. Teste gráfico ainda pendente. |
| Instalador | Falhas de dependências/bibliotecas podiam virar sucesso; o processo abria REPL ao terminar e havia alteração de `/etc/gai.conf`. | Propagação de erros, compilação antes das cópias, término explícito, prefixo sem sudo e nenhuma alteração de rede. |
| Desinstalador | Expansão de listas podia aplicar o prefixo apenas ao primeiro arquivo; erros eram ocultados. | Destinos individuais, sem remoção recursiva e sem apagar fontes. Teste preserva arquivo alheio à distribuição. |
| pkg-config | O metadado publicava a versão do Lua, não a do Santafé. | `Version: 2.0.2`. |
| Distribuição | Nomes de arquivos decompostos do macOS e recursos TLS de teste ausentes podiam quebrar testes em Linux. | Caminhos NFC, recursos obrigatórios e exclusão de configurações privadas. DKIM gera chave efêmera em vez de depender da máquina do autor. |
| Manual | A fonte completa ficava fora do repositório; a seleção do compilador podia usar outra árvore. | `docs/manual.html` e validador canônicos; seleção explícita de fonte respeitada; cópia local do portal sincronizada. |
| Ensaios de banco | Fixtures e verificações ainda esperavam versões antigas do esquema e textos antigos do Carteiro. | Esquema atualizado, senha sintética e consultas após criar cartas sintéticas; ensaio MariaDB isolado concluído. |
| Git/CI | O remoto consultado continuava em 1.0, com grande parte do desenvolvimento só no disco local. | Fontes consolidados no commit local `98f6bed`, manual incluído e CI Linux/macOS acrescentado. Nenhum push ou etiqueta estável foi feito nesta auditoria. |

## Validação executada

- Compilação nativa macOS do núcleo e das cinco bibliotecas C.
- Compilação e suíte completas também no Debian x86_64, a partir do arquivo
  distribuído e sem usar o núcleo instalado em produção. SLS, Unicode, manual,
  testes automatizados dos editores e MariaDB isolado passaram.
- Suíte `testar.sh`: sintaxe dos fontes, exemplos, bibliotecas, protocolos e
  aplicações; ensaios que exigem MariaDB são explicitamente separados.
- MariaDB 11.4 temporário e isolado: consultas preparadas, piscina/reconexão,
  Agência, IMAP/COPY/APPEND, autenticação, conversas, recepção, anexos, triagem,
  isolamento HTML, envio por destino local de teste, quarentena, recuperação e
  cópia/restauração. Nenhuma mensagem foi enviada a terceiros.
- Unicode: 766 casos oficiais, 1.990 fronteiras e entradas UTF-8 inválidas.
- AddressSanitizer/UndefinedBehaviorSanitizer: ensaios de Unicode, separador
  binário e precisão de índices, sem diagnóstico de falha nesses ensaios.
- WebAssembly recompilado e executado em Node: versão, tipos, ambiente,
  grafemas, bytes, separador binário, índices e matriz JSON vazia explícita.
- Instalação de arquivo distribuído em prefixo temporário com espaços; teste
  do núcleo, bibliotecas e `santafé-sls` instalado, sem sudo.
- Testes automatizados de VS Code e Sublime com interfaces simuladas; geração
  dos pacotes VSIX e `.sublime-package`.
- Manual: 1.237 IDs, 580 detalhes colapsáveis, 171 exemplos compilados, 258
  contratos C e 344 contratos Fé. Isso valida estrutura e contratos; não
  significa que todos os exemplos foram executados contra serviços externos.
- Inspeção do arquivo distribuído: caminhos NFC, ausência de ambientes
  privados/logs/binários de desenvolvimento e chave privada somente da fixture
  TLS local. A fixture é pública e jamais deve ser usada em produção.

## O que não foi confirmado

1. **Publicação e execução de CI.** O workflow foi criado, mas não foi executado
   no GitHub. O remoto permanece sem as correções até revisão/push apropriado.
2. **GUI dos editores.** Os testes automatizados não substituem abrir os
   pacotes finais no Sublime e VS Code, verificar o SLS e executar um arquivo.
3. **Portal em produção.** Manual e pacotes locais foram corrigidos; nenhum
   serviço foi reiniciado. O portal ainda precisa receber a versão aprovada,
   inclusive os executores WASM correspondentes.
4. **Windows, Apple Silicon e instalação das dependências em máquinas limpas.**
   Não foram revalidados nesta máquina macOS Intel. O instalador usa ferramentas
   externas do sistema; seus downloads não foram executados como parte da auditoria.

### Evidência Debian

Após autorização explícita do proprietário para a transferência e os testes,
o pacote de 514 arquivos correspondente byte a byte a `98f6bed` foi executado
em `/tmp/santafe-auditoria-2.0.2.SRwCBi` no `servidorsfdev`.
SHA-256: `f271dd0b32fbb0836107ceb0d25c5dcb87870d65fe8df850373f299446a64492`.
Resultado: `AUDITORIA_DEBIAN_2_0_2_OK`.

Os registros `compilacao.log`, `suite.log`, `mariadb.log`, `sublime.log` e
`vscode.log` foram preservados nesse diretório. O MariaDB de teste foi encerrado
e seu depósito temporário removido pelo ensaio. Não houve instalação, reinício
ou alteração de bancos de produção. As atualizações documentais posteriores
registram o resultado, sem mudar o código executado nesse teste.

## Contratos e limitações preservados

- `tamanho(colar)` mede grafemas; `#colar` e `octetos(colar)` medem bytes.
  Grafemas não medem pixels nem colunas de terminal.
- `tamanho(tabela)` segue a fronteira estrutural de `#`, não a quantidade de
  chaves; tabelas esparsas continuam exigindo escolha explícita de iteração.
- `tamanho(256)` não aceita número implicitamente. Use
  `tamanho(paraColar(256))`. `colar.tamanho` conserva sua coerção numérica.
- `json.matrizVazia` permite emitir `[]`; não se promete preservação automática
  da distinção `[]`/`{}` em toda decodificação e recodificação.
- O SLS diagnostica **sintaxe**. Análise semântica entre arquivos, depuração,
  resolução automática de dependências e gerenciador de bibliotecas não estão
  implementados só por existir autocompletar nos editores.
- Instalar em prefixo não padrão exige configurar caminhos de bibliotecas;
  ainda não é um instalador gráfico nem um pacote universal relocável.
- Pão do Café permanece uma implantação independente. Nenhum banco, conta,
  ambiente empresarial ou serviço dessa empresa foi alterado.

## Por que a versão maior é 2.0

Código antigo pode depender de `"booleano"`, `_ENV`, nomes de compatibilidade
removidos ou medidas em bytes. Essas premissas deixam de valer na linha 2.0.
O guia `MIGRACAO-VOCABULARIO-LOGICO.md` descreve a migração. Correções desta
auditoria seguem em 2.0.2, sem reescrever artefatos históricos imutáveis.

## Como reproduzir

```sh
make cbin cbibc
bash testar.sh
python3 testes/integracao/testar_instalador.py
python3 extensões/sublime/testes/testar_pacote.py
python3 extensões/vscode/testes/testar_extensao.py
node extensões/vscode/testes/testar_comportamento.js
node extensões/vscode/testes/testar_sls.js
bash testes/integracao/testar_correio_mariadb.sh
make dist
python3 testes/integracao/testar_distribuicao.py dist/santafe-2.0.2.tar.gz
```

O ensaio MariaDB requer as ferramentas de servidor MariaDB e portas locais
livres; pode receber `MARIADB_PREFIXO`. Os testes não autorizam usar bancos de
produção. Para WASM, carregue o Emscripten, execute `(cd src && bash emscripten.sh)` e rode
`node testes/integracao/testar_wasm.js`.

Referências usadas nas correções de editor: [ambientes Python do Sublime](https://www.sublimetext.com/docs/api_environments.html)
e [sistemas de execução do Sublime](https://www.sublimetext.com/docs/build_systems.html).
