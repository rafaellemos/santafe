# Auditoria da linha Santafé 2.0 — 17 de outubro de 2026

## Parecer

A mudança de versão maior **2.0 é justificada**, pois há alterações incompatíveis
no vocabulário e no comportamento público. Isso não equivale a confirmar que
todas as instalações já executam o mesmo artefato ou que não existem defeitos.

O fechamento consolida **2.0.2**, SLS **0.1.1**, VS Code **1.0.6** e Sublime
**1.0.13**. As suítes originais em macOS e Debian passaram. As pendências
gráficas foram corrigidas e retestadas nos editores reais em macOS Intel,
inclusive as paletas e os dois curingas. Não se declara homologação de
plataformas que não foram ensaiadas nem se substituem arquivos históricos.

## Situação consolidada — 19/10/2026

Esta seção e [LANCAMENTO-2.0.2.md](LANCAMENTO-2.0.2.md) prevalecem sobre os
estados históricos registrados em cada rodada abaixo.

- VS Code 1.0.6 e Sublime 1.0.13: publicação pública e ativação local
  confirmadas; arquivos instalados correspondem aos pacotes auditados.
- Realce: 55 regressões em cada editor; 40 verificações dirigidas de
  concatenações no VS Code e 43 no Sublime; 610 entradas da API por editor.
  Paleta suave reversível; `®`/`Ⓡ` e chaves externos laranja sem itálico;
  expressões internas continuam código. Documentos e preferências preservados.
- Conferência operacional: página oferece núcleo 2.0.1, executável do servidor
  anuncia 1.0.0, SLS/WASM anteriores à auditoria. Esses itens requerem o novo
  publicador; a atualização dos editores não os instalou implicitamente.
- Empacotamento: corrigida a omissão do runtime Oniguruma `.wasm` nos fontes
  TAR/ZIP. Recursos do editor e licenças acompanham a distribuição; capturas
  locais são excluídas. Não há mudança de linguagem nesta correção.
- Git: o fechamento registra os fontes, testes, documentação e publicador.
  Commit/tag locais não equivalem a envio ao remoto ou execução de CI.
- Limites mantidos: sem homologação Windows/Apple Silicon, sem provisionamento
  completo de dependências em máquina limpa e sem alegar aprovação de CI não
  observada. Pão do Café e bancos de produção permanecem fora do escopo.

Escopo: mudanças recentes de vocabulário, grafemas, índices, compatibilidade,
SLS, extensões, instalação, distribuição, documentação e regressões disponíveis
do ecossistema. Não é uma certificação de segurança completa de todo o código
herdado ou um teste de carga prolongado de produção.

### Revalidação do fechamento — 19/10/2026

Correção após a tentativa de publicação: o ensaio comum havia passado, mas
a execução com sudo revelou colisão com fixtures fixas em `/tmp` pertencentes
a `rafael`, bloqueada por `fs.protected_regular=2`. Nenhum arquivo operacional
foi trocado. A revisão 2 isola cada fixture em diretório `0700`, preserva os
arquivos históricos e acrescenta ensaios concorrentes e limpeza após falha.
O marcador Git original é preservado; `v2.0.2-r2` registra essa correção.

- macOS Intel: repetidas a suíte nativa, a integração MariaDB isolada, a
  instalação em prefixo temporário, a verificação dos dados Unicode e a
  compilação/execução WebAssembly. Nenhum banco de produção foi acessado.
- Editores: reconstruções VSIX/Sublime correspondem byte a byte aos arquivos
  públicos 1.0.6/1.0.13. Regressões de realce, concatenações, API/paletas e
  ciclo de vida do SLS passaram; nesta rodada não se alteraram as extensões.
- Debian: o lançador foi ensaiado como `rafael`, em `/tmp`, com compilação
  nativa, suíte, instalação isolada, WebAssembly, manual e preparo do plano
  operacional. Resultado: `FECHAMENTO_2_0_2_PREFLIGHT_OK`; nenhuma instalação
  ou reinicialização de serviço. Os ensaios MariaDB do Debian são os da
  rodada anterior; a repetição de banco desta rodada ocorreu no Mac.
- O núcleo novo também importou as bibliotecas já instaladas no Debian,
  sem abrir conexões de banco nem alterar bibliotecas de produção.
- Publicador: regressões de alteração concorrente, destino simbólico,
  versão imutável, instalação e restauração após falha parcial passaram.
  A compilação usa cache temporário do Emscripten, sem mudar permissões
  do SDK compartilhado.
- Distribuição: TAR e ZIP conferidos arquivo a arquivo e por SHA-256;
  runtime Oniguruma e licenças presentes. O pacote não inclui os registros
  gráficos locais da auditoria. O registro Git e o envio ao servidor não
  significam que a publicação privilegiada já foi executada.

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
| Sublime | Requisito Python restritivo, comentários/colares longos incompletos, nomes Unicode e fechamento de blocos. | Metadados Python 3.8/3.14, realce atualizado e conclusões aninhadas. O primeiro ensaio gráfico revelou que o Enter não era carregado; corrigido em 1.0.9 com `Default.sublime-keymap` e regras de indentação, confirmado na interface. |
| VS Code — símbolos | Declarações após linhas vazias produziam intervalos inválidos. | Espaço horizontal na expressão regular, posição real do nome e regressões LF/CRLF/Unicode; navegação gráfica confirmada em 1.0.2. |
| Realce embutido | Interpolação incompleta e ausência de HTML/JS em colares. | Gramáticas dos editores reutilizadas; `®var`, `Ⓡvar`, `®{expressão}`, chaves aninhadas, escapes e anotações de linguagem. Trinta casos nos motores reais de cada editor, além da inspeção visual. |
| Execução no Sublime | O arquivo era inserido em um comando de shell; o PATH de aplicativos gráficos podia não encontrar o núcleo. | Argumentos separados e procura nos prefixos de instalação; ensaio com espaços e metacaracteres no nome. Execução gráfica com o núcleo temporário 2.0.2 confirmada em 18/10. |
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

## Primeiro ensaio gráfico de 18 de outubro de 2026

Ambiente: macOS 15.7.7 Intel, VS Code 1.142.0 e Sublime Text build 4215.
Artefatos: VSIX Santafé 1.0.1 e pacote Sublime 1.0.8, usando o núcleo 2.0.2
e o SLS 0.1.1 instalados anteriormente em prefixo temporário com espaços.
Foram usados somente arquivos sintéticos. VS Code recebeu perfil e diretório
de extensões próprios; Sublime foi ensaiado em modo seguro, com dados separados.
Os pacotes e o núcleo da instalação habitual não foram substituídos.

| Recurso observado | VS Code | Sublime |
| --- | --- | --- |
| Realce e identificador `índice` sem separar o `e` | Passou | Passou |
| Conclusão `para` por Tab, com recuo e `fim` | Passou | Passou |
| Erro sintático de `fim` ausente | Apareceu no painel de problemas | Apareceu como marcador e sublinhado no editor |
| Remoção do diagnóstico após corrigir o fonte | Passou | Passou |
| Execução do núcleo 2.0.2 dentro do editor | Passou com tarefa de teste explícita | Passou com o sistema de execução Santafé e PATH temporário |
| Reinício do SLS | Passou pelo comando da extensão | Não ensaiado pelo comando de reinício do cliente |
| Lista de símbolos/funções | Falhou com exceção de intervalo | Não ensaiada |
| Enter após `função teste(índice)` | Não ensaiado | Não acrescentou `fim` nem o recuo esperado |

No Sublime foi instalado o cliente LSP 2.15.0 e suas dependências somente no
perfil seguro. O caminho do SLS foi configurado explicitamente nesse perfil.
Isso comprova a comunicação real editor/SLS, mas não homologa a instalação
automática pelo comando “Ativar diagnósticos SLS” em uma máquina limpa.
Na execução pelo VS Code foi criada uma tarefa de processo para o teste;
não se afirma que a extensão forneça esse atalho de execução por padrão.

### Pendências encontradas nessa rodada (corrigidas na segunda rodada)

1. **VS Code — símbolos de funções após linhas vazias.** Ao abrir o arquivo
   de teste, o extension host registrou `selectionRange must be contained in
   fullRange`, em `símbolosDoDocumento`, `extension.js:164`. A expressão
   `^\s*` pode consumir quebras de linha antes da declaração, enquanto o
   intervalo inteiro é limitado à primeira linha da correspondência e a
   seleção do nome é calculada como se tudo estivesse nessa linha. É preciso
   corrigir os intervalos e incluir regressões com linhas vazias e CRLF.
   O erro não impediu os diagnósticos sintáticos do SLS.
2. **Sublime — fechamento pelo Enter não confirmado na interface real.**
   O gabarito `para` aceito com Tab gerou o bloco correto. Porém, após inserir
   `função teste(índice)` e pressionar Enter, o editor apenas abriu uma linha
   vazia, sem `fim` e sem recuo. Revisar o carregamento do atalho
   `santafe_nova_linha`, o arquivo `.sublime-keymap` e as regras de indentação;
   não considerar o teste simulado suficiente para aprovar esse comportamento.

Durante a automação, o menu nativo View prendeu a sessão temporária do Sublime.
A amostra da pilha mostrou espera no laço de eventos de menu do AppKit; isso
não é evidência de falha do SLS. O perfil seguro foi guardado, a instância
temporária reiniciada e o teste visual de diagnóstico concluído. Ao terminar,
a sessão normal do Sublime foi reaberta no projeto que já estava aberto.
Nenhum serviço de produção, etiqueta Git ou pacote distribuído foi alterado.

### Capturas do ensaio

- VS Code: [diagnóstico](evidencias/editores-20261018/vscode-diagnostico.png),
  [diagnóstico removido](evidencias/editores-20261018/vscode-diagnostico-limpo.png),
  [gabarito](evidencias/editores-20261018/vscode-snippet.png) e
  [execução](evidencias/editores-20261018/vscode-execucao.png).
- Sublime: [gabarito](evidencias/editores-20261018/sublime-snippet.png),
  [Enter sem fechamento](evidencias/editores-20261018/sublime-enter-fim.png),
  [execução](evidencias/editores-20261018/sublime-execucao-202.png),
  [diagnóstico](evidencias/editores-20261018/sublime-sls-erro.png) e
  [diagnóstico removido](evidencias/editores-20261018/sublime-sls-corrigido.png).

## Segunda rodada — correções e realce embutido, 18 de outubro

Mesmo macOS Intel e mesmos editores; pacotes **VS Code 1.0.2** e **Sublime
1.0.9**, núcleo temporário 2.0.2 e SLS 0.1.1. As capturas abaixo foram feitas
nos aplicativos reais, com os pacotes instaláveis finais, não em uma simulação.
O perfil seguro do Sublime foi recriado e não continha uma pasta `Packages/Santafe`
sobrepondo os arquivos do pacote. Os testes não substituíram as instalações
habituais e não alteraram produção.

| Verificação | Resultado |
| --- | --- |
| VS Code: símbolos após duas linhas vazias | `cumprimentar` aparece na navegação; nenhuma exceção de intervalo no extension host. |
| Sublime: Enter após `função teste(índice)` | Insere linha com quatro espaços e `fim`; cursor permanece no corpo. |
| Gabaritos `®var` e `®{expressão}` | Realce confirmado nos dois editores, inclusive em atributos HTML e strings JS. |
| HTML e JS em colares | Tags, atributos, declarações e funções realçados; retorno à sintaxe Santafé após fechar o colar. |
| Diagnósticos SLS nos dois editores | `fim` ausente sinalizado; diagnóstico removido após corrigir e salvar. |
| Execução nos dois editores | Núcleo 2.0.2 executa o arquivo com gabaritos, grafemas, octetos e `maiorÍndice`; Sublime pelo sistema de execução do pacote, VS Code por tarefa explícita de teste. |
| Reinício do SLS no VS Code | Comando da extensão reinicializa o servidor e volta a sincronizar os arquivos, sem erros. |
| Regressões automatizadas | Comportamento e empacotamento dos dois editores; ciclo de vida/confiança do SLS no VS Code; gerador de gramáticas idempotente. |
| Motores de realce reais | 30 casos aprovados no TextMate/Oniguruma do VS Code e 30 no motor do Sublime com o pacote instalado. |
| Manual | Novamente validado: 1.237 IDs, 580 detalhes, 171 exemplos, 258 contratos C e 344 contratos Fé. |

Além das duas pendências, o teste real detectou uma variável interna acentuada
que não era expandida pela gramática do Sublime. Renomeada para `funcao_global`,
restabelecendo o realce de `mostre`, `tamanho` e demais funções globais.
O empacotador passou a incluir as gramáticas auxiliares HTML/JS e o atalho padrão.
O exportador do repositório Sublime preserva o README completo e grava JSON válido.

HTML é detectado pela marcação inicial na linha de abertura; JS pelo comentário
`/* javascript */` ou `/* js */`. Para conteúdo iniciado na linha seguinte,
use `--[[html]]` ou `--[[javascript]]` imediatamente antes do delimitador.
Essas anotações são comentários válidos da linguagem: não alteram o núcleo.
O recurso é **realce**, não análise semântica de HTML/JS. Colares comuns não
ganham interpolação. Na forma curta, os nomes ASCII seguem o contrato do núcleo;
para identificadores Unicode, use `®{índice}`.

Evidências da rodada final:

- VS Code: [símbolos corrigidos](evidencias/editores-correcao-20261018/vscode-simbolos-final.png),
  [realce HTML/JS e gabaritos](evidencias/editores-correcao-20261018/vscode-realce-final.png),
  [diagnóstico](evidencias/editores-correcao-20261018/vscode-erro-final.png),
  [diagnóstico removido](evidencias/editores-correcao-20261018/vscode-corrigido-final.png) e
  [execução](evidencias/editores-correcao-20261018/vscode-execucao-final.png).
- Sublime: [Enter com recuo e fim](evidencias/editores-correcao-20261018/sublime-enter-final.png),
  [realce HTML/JS e gabaritos](evidencias/editores-correcao-20261018/sublime-realce-final.png),
  [diagnóstico](evidencias/editores-correcao-20261018/sublime-erro-final.png),
  [diagnóstico removido](evidencias/editores-correcao-20261018/sublime-corrigido-final.png),
  [execução](evidencias/editores-correcao-20261018/sublime-execucao-final.png) e
  [30 casos de escopos](evidencias/editores-correcao-20261018/sublime-scopes.json).

Artefatos locais gerados naquela rodada (ainda não publicados):

- `extensões/vscode/dist/santafe-1.0.2.vsix` — SHA-256
  `5ccc34534bb9ca30f73af17a64cd758b56591d4b546fe0dc40400ae486c60e8e`.
- `extensões/sublime/dist/Santafe-1.0.9.sublime-package` — SHA-256
  `e916887902b7b768b8300144c5f6761d964de55471c04936047469e887c08ead`.
- Instalação manual: `extensões/sublime/dist/Santafe.sublime-package` — SHA-256
  `3b95d721df11189d373dfe7c90644041fd9beeffeb6c25f41dc8ad162f4c4e3d`.
  Este é o arquivo instalado no ensaio; a variante do Package Control tem os
  mesmos recursos, sem `package-metadata.json`, que o gerenciador acrescenta.

## Complemento — curinga realçado por inteiro

Após a segunda rodada, foi apontado que o curinga `®` herdava a cor do colar,
enquanto apenas o nome da variável recebia destaque. O teste anterior conferia
o nome, mas não o curinga. Corrigido em **VS Code 1.0.3 e Sublime 1.0.10**:

- `®var` e `Ⓡvar` são um único token com estilo de variável.
- `®{`/`Ⓡ{` e `}` recebem estilo de operador; a expressão mantém seus tokens.
- Sequências escapadas e colares comuns continuam sem interpolação.
- A suíte compartilhada passou a verificar todos os caracteres de cada trecho:
  **42 casos** aprovados nos motores reais TextMate e Sublime.
- As cores calculadas pelo TextMate foram verificadas nos temas Dark+ e Monokai.
  No Sublime, Monokai exibiu curinga e variável no mesmo laranja; delimitadores
  de expressão em rosa, diferentes do amarelo do texto. Instância segura nova,
  com o pacote final instalado, sem tocar na instalação habitual.

Evidências: [captura do curinga](evidencias/editores-curinga-20261018/sublime-curinga.png)
e [resultados e cores do Sublime](evidencias/editores-curinga-20261018/sublime-resultado.json).
O núcleo e o SLS não mudaram neste complemento. Pacotes atuais, ainda locais:

- `extensões/vscode/dist/santafe-1.0.3.vsix` — SHA-256
  `e86ea6845eb6c068467b75b753a222d2a3c1a1716e6ea5fcc1c0a834717c5770`.
- `extensões/sublime/dist/Santafe.sublime-package` (manual, 1.0.10) — SHA-256
  `d2f31fb03fb9132e76642f4b28fa4bbf95769a6d174f9b0c718de7588adccf73`.
- `extensões/sublime/dist/Santafe-1.0.10.sublime-package` (Package Control) — SHA-256
  `a2a0eff0cff96fb640763adb2334c44fa9ea75df9442e51f86e841e479253f84`.

## Publicação dos editores preparada — 18 de outubro

Por solicitação do proprietário, o publicador e o pacote foram enviados ao
`servidorsfdev`. O modo `--preflight` passou no Debian, sem sudo, sem instalar
arquivos e sem reiniciar serviços: somas, conteúdo dos pacotes, página preparada
e compilação com o `santafec` do servidor foram conferidos.

O empacotador VSIX passou a fixar os metadados ZIP, tornando duas execuções
idênticas byte a byte. O conteúdo da extensão não mudou; a soma atual acima
é a do arquivo reproduzível incluído no envio. O publicador preserva os downloads
do núcleo, atualiza somente `/baixar`, os pacotes, SHA256SUMS e o catálogo Sublime;
salva backup e restaura os arquivos em caso de falha. Os testes cobrem preparo
idempotente, preservação do núcleo e recusa de fontes divergentes ou artefatos
versionados conflitantes.

Arquivos enviados:

- `/tmp/publicar-editores-corrigidos-v1.sh` — SHA-256
  `260855186b2e369c19abc37e6ffc77b4d6b9f186f17d7e93d518b4aa38514c58`.
- `/tmp/santafe-editores-vscode-1.0.3-sublime-1.0.10.tar.gz` — SHA-256
  `103888dc2c90a6df0a69f372b2754e289ab6c5c1f24fb35c631d331dbd94b83e`.

A instalação aguarda o comando do usuário:
`sudo bash /tmp/publicar-editores-corrigidos-v1.sh`.
O envio e a pré-validação não significam que o portal já tenha sido atualizado.

## O que não havia sido confirmado na rodada original (histórico)

1. **Publicação e execução de CI.** O workflow foi criado, mas não foi executado
   no GitHub. O remoto permanece sem as correções até revisão/push apropriado.
2. **Instalação automática completa dos editores/SLS em máquina limpa.** As duas
   pendências gráficas estão corrigidas e o reteste passou. Isso não homologa o
   fluxo completo de instalação automática: o SLS deste ensaio foi configurado
   em prefixo temporário e o cliente LSP do Sublime foi preparado explicitamente.
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

## Regressão HTML concatenado — 18 de outubro

O exemplo completo enviado pelo proprietário foi preservado em
`extensões/testes/html-concatenado.fé` e compila no núcleo sem modificações.
Foram reproduzidas e corrigidas duas falhas da detecção automática: doctype
minúsculo e fragmentos concatenados iniciados por texto antes de uma tag.
A procura de tags não ultrapassa o delimitador do colar.

O `escapeHTML` isolado já passa nas gramáticas novas. As instalações normais
deste Mac ainda eram VS Code 0.1.0 e Sublime 1.0.7, sem as correções de colares
simples/longos dos testes isolados anteriores. Foram atualizadas para VS Code
1.0.4 e Sublime 1.0.11; a cópia anterior do Sublime está em
`/tmp/santafe-html-realce.PYTZOL/sublime-normal-anterior.sublime-package`.

- TextMate/Oniguruma real: 55 casos aprovados, mais cores Dark+/Monokai.
- Sublime real, sessão isolada: 55 casos, zero falhas.
- Conclusões, símbolos, ciclo de vida SLS, empacotamento e preparo do publicador:
  aprovados; nenhum contrato do núcleo foi alterado.
- Limite conhecido e documentado: o TextMate pode manter um contexto embutido
  quando a concatenação corta um atributo HTML entre aspas ou comentário JS.
  O exemplo solicitado concatena texto entre tags e não sofre desse limite.

Arquivos enviados ao servidor, pré-validação Debian aprovada sem sudo:

- `/tmp/publicar-editores-corrigidos-v2.sh` — SHA-256
  `06b61c8c144d03bf2a670af8f48db2eea39d9171f6745f9a53f16e0ce17f0edd`.
- `/tmp/santafe-editores-vscode-1.0.4-sublime-1.0.11.tar.gz` — SHA-256
  `4b450d8144b103f530cb940240a083f7aa858285f5635e7bbb3ca8d1704b05ed`.

O portal não foi instalado nesta rodada; aguarda
`sudo bash /tmp/publicar-editores-corrigidos-v2.sh`. O publicador preserva
artefatos antigos e reinicia somente `sfdev.service`.

## VS Code 1.0.5 — concatenações dentro de atributos/comentários (18/10/2026)

Supera o limite registrado na revisão 1.0.4: em vez de entregar o fechamento
do colar a um contexto HTML/JS aninhado do TextMate, recorta primeiro os
literais Santafé. Uma expressão concatenada vira um documento virtual com
espaços reservados para os operandos dinâmicos. As gramáticas nativas HTML,
JavaScript e CSS preservam o estado entre fragmentos; somente posições que
pertencem ao conteúdo literal recebem cores. Não há execução, eval, leitura
de imports ou envio de fonte à rede.

- Base TextMate segura, sem incluir gramáticas capazes de esconder `]]`.
- API pública `DocumentSemanticTokensProvider`; trata-se de realce léxico,
  não de nova análise semântica pelo SLS. Runtime TextMate/Oniguruma e suas
  licenças acompanham o VSIX. Nenhum `npm install` é necessário ao usuário.
- Cobertura: 55 casos anteriores, 40 verificações novas; UTF-16, CRLF,
  escapes, `®`/`Ⓡ`, delimitadores com até 100 sinais `=`, cancelamento,
  mudanças de versão, ausência de sobreposição e 3.000 fragmentos.
- VSIX instalado em perfil isolado: provedor registrado no Extension Host
  real e realce atualizado após edição; evidência em
  `evidencias/vscode-concatenacoes-20261018/host-vsix.json`.
- Inspeção visual Dark+ e Monokai: atributos retomados, comentários JS,
  expressões intermediárias, curingas e `escapeHTML` corretos. Capturas na
  mesma pasta de evidências. O texto literal sem estilo nativo específico
  pode conservar a cor-base do colar conforme o tema.
- Conclusões, navegação, ciclo de vida do SLS, empacotamento reproduzível,
  preparo idempotente do publicador e validador do manual aprovados.
- Limites defensivos de tamanho, profundidade e tempo documentados no README;
  o conteúdo dos operandos dinâmicos não é avaliado. Desabilitar tokens
  semânticos conserva o realce básico Santafé.
- Sublime 1.0.11 preservado byte a byte: não recebeu alteração nesta rodada.

O VS Code local foi atualizado para 1.0.5; recarregar sua janela ativa a nova
extensão. Somente a janela de testes isolados foi encerrada. O núcleo, SLS e
os serviços de produção não foram alterados.

Arquivos enviados a `servidorsfdev`, conferidos por SHA-256 e pré-validados
sem sudo/instalação/reinício:

- `/tmp/publicar-editores-corrigidos-v3.sh`:
  `ed700ef111f918fad37632f4874b2ac75b3f541be42bce62450d024bd8302298`.
- `/tmp/santafe-editores-vscode-1.0.5-sublime-1.0.11.tar.gz`:
  `1b1a0cd05ba5ca7b8f5750387c0663922913b22a41e14edb8bfdc012b5297802`.
- VSIX 1.0.5:
  `a4b3b292358abb7e8f4d83fff9ad788e549eae7bccd514a49c4e3c7e19d743cb`.

A publicação do portal aguarda `sudo bash /tmp/publicar-editores-corrigidos-v3.sh`.
Não confundir a pré-validação com instalação. O publicador atualiza página e
downloads, preserva artefatos históricos e reinicia somente `sfdev.service`.
A revisão textual do manual está no fonte; este publicador não instala o manual.

Referência da API: https://code.visualstudio.com/api/language-extensions/semantic-highlight-guide

## Sublime 1.0.12 — continuidade de HTML/JS (18/10/2026)

Confirmação anterior no Sublime 4215: a versão 1.0.11 falhava em seis de
15 verificações dirigidas a concatenações. O fragmento posterior perdia o
contexto do atributo HTML ou do comentário JS. Não era falha do núcleo/SLS.

A revisão 1.0.12 recorta literais e concatenações em Python, conserva o mapa
de posições Unicode e usa HTML/JS nativos sobre documentos virtuais. As cores
voltam apenas ao conteúdo literal, por regiões de primeiro plano. Expressões
Santafé, delimitadores e `®`/`Ⓡ` não recebem o estilo do trecho virtual.
Não executa código, importa fontes do usuário nem usa rede, Node ou LSP.

- 43 verificações novas aprovadas no Sublime real: atributos, comentários
  JS de linha/bloco, HTML com script, delimitadores mistos ou longos, escapes,
  Unicode/CRLF, expressões agrupadas, isolamento e entradas incompletas.
- 55 regressões anteriores aprovadas; edição real, descarte por versão,
  limpeza de regiões e limites defensivos também conferidos.
- Monokai, Mariana, Celeste, Breakers e Sixteen verificados com regiões
  efetivamente aplicadas. Inspeção visual de Monokai e Mariana; capturas e
  relatórios em `evidencias/sublime-concatenacoes-20261018/`.
- Esquemas próprios precisam da regra transparente `meta.santafe-embedded`,
  descrita no README. Sem ela, mantém-se a gramática básica, sem a camada
  de continuidade. Limites e ausência de avaliação dinâmica documentados.
- Pacotes e catálogo reproduzíveis; testes do publicador e do manual aprovados.
- Os 43 casos também passaram usando somente o `.sublime-package` final,
  sem pasta de desenvolvimento sobreposta. O Package Control foi isolado
  temporariamente para não reinstalar a versão pública 1.0.11 durante esse
  ensaio; configuração e instalação local anterior restauradas ao final.
- VSIX 1.0.5 preservado byte a byte. Nenhuma alteração no núcleo ou SLS.

Arquivos enviados ao `servidorsfdev`, conferidos por SHA-256 e pré-validados
sem sudo, instalação ou reinício:

- `/tmp/publicar-editores-corrigidos-v4.sh`:
  `ccd91779b8e01f0a64e025c47891aa6451cdcb7b2dfa6249a32c66489ed07b59`.
- `/tmp/santafe-editores-vscode-1.0.5-sublime-1.0.12.tar.gz`:
  `e32a2d971c6ffc73cf6ba13adf6cb12e33b6ac7ac28f2789019f38e6899e2112`.
- Pacote manual Sublime 1.0.12:
  `a9f87953766e648243a0c5bbd892ac58805fcb71f161753be79391d36f78a7cd`.
- Pacote Package Control 1.0.12:
  `2f171baef48bdf5a7d3e2ec362f68e00c8563f25b9d6bbf9af9b54b702190118`.

Publicação pendente do comando `sudo bash /tmp/publicar-editores-corrigidos-v4.sh`.
O publicador atualiza somente página, pacotes e catálogo, com cópia reversível;
reinicia apenas `sfdev.service`. A revisão do manual está no fonte e não é
instalada por esse publicador. Correio e Pão do Café permanecem intocados.

Referências: [API de regiões](https://www.sublimetext.com/docs/api_reference.html)
e [esquemas de cores](https://www.sublimetext.com/docs/color_schemes.html).

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

Para reproduzir o realce, execute `extensões/vscode/testes/testar_realce.js`
com o Electron do VS Code (`ELECTRON_RUN_AS_NODE=1`) e `--app` apontando para
seu diretório `Resources/app`. No Sublime com o pacote instalado, execute na
console `runpy.run_path` sobre `extensões/sublime/testes/verificar_realce.py`.
Ambos usam os mesmos casos em `extensões/testes/realce.json`.

Referências usadas nas correções de editor: [ambientes Python do Sublime](https://www.sublimetext.com/docs/api_environments.html)
e [sistemas de execução do Sublime](https://www.sublimetext.com/docs/build_systems.html).
