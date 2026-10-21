# SLS — Servidor de Linguagem Santafé

O SLS roda localmente, como processo filho do editor, e conversa pelo protocolo
LSP (JSON-RPC 2.0 sobre entrada e saída padrão). Ele não abre porta de rede,
não executa o código editado nem envia o fonte a terceiros.

## Perfil 1.0.0 — publicado com a Santafé 2.1.0

A evolução para 1.0 está definida em
[SLS 1.0 — contrato e bateria de aceitação](SLS-1.0.md).
Esse contrato distingue recursos existentes de pendências e não altera a versão
do servidor instalado. As versões dos pacotes dos editores não são a versão do SLS.

O perfil atende `initialize`, `shutdown` e o ciclo completo de documento:

- `textDocument/didOpen`;
- `textDocument/didChange` com sincronização incremental e substituição integral;
- `textDocument/didSave`;
- `textDocument/didClose`.

Em cada abertura, alteração ou salvamento, o SLS chama `depure.analise` com o
texto sincronizado. A API usa o analisador sintático real do núcleo, descarta a
função compilada e nunca a executa. O primeiro erro recebe o intervalo do token
original, em octetos, convertido para linhas e colunas UTF-16. Emoji, acentos
combinados, CRLF, CR e URI contendo dois-pontos não deslocam o diagnóstico.
Um erro de fim de arquivo tem intervalo vazio no fim do documento; literais ou
comentários incompletos podem abranger várias linhas. Erros sem token, como
bytecode recusado, têm código `sintaxe-sem-intervalo` e posição inicial neutra.

**Recompile e instale núcleo e SLS juntos.** Esta revisão depende da nova API
`depure.analise`, `depure.lexemas` e do módulo privado POSIX `sls/nativo.so`,
ausentes nos binários publicados da Santafé 2.0.3. O servidor
recusa a inicialização com explicação clara quando a API não existe. A versão do
núcleo exigida é Santafé 2.1.0, publicada e conferida em 21/10/2026;
não reutilize o rótulo 2.0.3 para estes binários modificados.

### Contrato do analisador

`depure.analise(fonte [, nome])` aceita texto, não leitores nem coerção numérica.
Devolve `verdadeiro` no sucesso ou `falso, diagnóstico` em erro sintático.
O diagnóstico contém `mensagem`, `código = "sintaxe"` e, quando há token,
`início`/`fim`: offsets de octetos, base zero, fim exclusivo. Falhas que não são
sintáticas continuam sendo erros, não diagnósticos inventados. `carregue` mantém
seu contrato anterior. A API C aditiva `lua_loaddiagnostic` recebe a mesma entrada
de `lua_load` mais um `lua_Diagnostic *` opcional, com campos `start`, `end` e
`hasrange`; conserva os códigos de retorno e a pilha de `lua_load`.

### Sincronização incremental

O servidor anuncia `TextDocumentSyncKind.Incremental` (2). Cada lote é aplicado
em ordem, sempre sobre o resultado da mudança anterior, e confirmado somente
se todas as mudanças forem válidas. Versões antigas ou repetidas são ignoradas.
Uma coluna além do fim da linha é limitada ao fim, conforme LSP 3.17; posições
fora das linhas existentes ou que cortam um par UTF-16 são recusadas.

Um lote inválido preserva o último texto confirmado, marca o documento como
dessincronizado, limpa os diagnósticos antigos e emite `window/logMessage`
solicitando texto integral ou fechamento/reabertura. LSP não define um pedido
genérico do servidor para forçar esse reenvio: não há recuperação automática
prometida. Deltas seguintes não são analisados até a ressincronização.
`didSave` não reabre documentos fechados nem sobrescreve versões.

O **transporte e o espelho de texto** são incrementais; a indexação de linhas,
a compilação sintática e a construção dos escopos percorrem o documento completo.
Não há parser incremental. O lexer real alimenta uma análise estrutural limitada,
com escopos, vínculos e recuperação de erros. Só quando o compilador rejeita o
fonte, diagnósticos recuperados são acrescentados ao primeiro erro: até 16,
com código `sintaxe-recuperada`. Essa recuperação não substitui o compilador.

### Recursos semânticos

- Conclusões das globais, bibliotecas padrão/C/Fé e variáveis visíveis; aliases
  de importações literais e membros exportados estaticamente.
- Hover e ajuda de parâmetros baseados no mesmo catálogo extraído do manual.
- Definição, referências, destaques e símbolos do documento/projeto.
- Renomeação com verificação de escopo, colisões e capturas; edições versionadas
  para documentos abertos e versão nula para arquivos fechados, conforme LSP.
  O servidor **nunca grava** essas edições: o editor as apresenta/aplica.
- Formatação conservadora do recuo, preservando comentários, literais e CRLF;
  dobramento, seleção estrutural e proposta de `fim` ausente somente quando o
  compilador confirma que a adição torna o programa sintaticamente válido.
- Tokens semânticos de variável, função e parâmetro. Os editores preservam
  separadamente a paleta de HTML/JS e os marcadores laranja dos gabaritos.

Renomeações com análise incompleta, escapes de gabaritos sem mapeamento seguro,
aliases reatribuídos e usos dinâmicos de campos são recusadas. A recusa é
deliberada: não se deve editar apenas as referências que foi possível descobrir.
Isso não é inferência completa de tipos nem avaliação do programa.
Globais dinâmicos também não oferecem renomeação. Uma variável local é
analisada somente no seu documento; não depende do limite do índice de projeto.
Antes de renomear, o SLS descarta o cache de fontes fechados e relê o projeto.

## Uso pelo editor

Após a instalação, o comando é:

```text
santafé-sls
```

O cliente do editor deve iniciá-lo por `stdio`; não use TCP nem acrescente
argumentos que produzam texto em `stdout`, pois essa saída pertence integralmente
ao protocolo LSP. O SLS anuncia codificação de posição `utf-16`, a convenção
esperada pelo VS Code e por clientes LSP compatíveis.

O iniciador usa `-E -P`: ignora `LUA_INIT`/caminhos Lua do ambiente e não ativa
o carregador de dependências do diretório atual. O SLS lê a geração travada
separadamente, sem executar seus módulos. Configurações personalizadas que
chamam o binário diretamente devem conservar essas duas opções.

### VS Code

O cliente do VS Code fica em
[`extensões/vscode`](../extensões/vscode). A versão 1.1.0 reconhece arquivos
`.fé` e `.fe`, aplica realce, trechos e regras básicas de edição, oferece
conclusões das palavras da linguagem e da API pública, ajuda rápida, estrutura
de funções e navegação para funções declaradas no arquivo aberto. Ela inicia
`santafé-sls` automaticamente. Quando o servidor anuncia recursos semânticos,
o cliente encaminha os pedidos a ele, sem duplicar os provedores locais. Sem
servidor, ou com uma versão que não oferece o recurso, mantém o fallback local.
Cancelamentos, reinício, versões e alterações incrementais são encaminhados.

Empacote a extensão com:

```bash
cd extensões/vscode
python3 empacotar.py
```

Instale o arquivo gerado em `dist/` pela opção **Extensions: Install from
VSIX...** do VS Code. O comando `santafé-sls` precisa estar disponível na
mesma máquina em que o VS Code executa a extensão. Em uma sessão Remote SSH,
isso significa o computador remoto, não o computador local. Para uma compilação
local do próprio repositório, basta `make cbin`: a extensão usa automaticamente
`src/santafé` com `ferramentas/sls/sls.fé`. Para outros projetos, use
`make cbin ibin isls` para instalar o inicializador `santafé-sls`.

### Sublime Text

A versão 1.1.0 está em [`extensões/sublime`](../extensões/sublime). Ela
reconhece `.fé` e `.fe`, fornece realce, snippets, conclusões da API pública,
ajuda curta e os comandos de execução e verificação sintática em
**Tools → Build System**.

O Sublime Text não traz um cliente LSP. Execute **Santafé: Ativar diagnósticos
SLS** para configurar o iniciador e solicitar o cliente **LSP** ao Package Control.
A configuração manual de exemplo continua disponível. Assim como no VS Code, `santafé-sls` deve estar disponível no `PATH`
do processo do editor. O pacote LSP usa o mesmo servidor e negocia as capacidades;
conclusões/hover locais ficam desativados apenas quando uma sessão ativa oferece
o respectivo recurso. Os snippets e o realce independente continuam disponíveis.
O exemplo inclui `file_watcher` para `.fé` e `.fe`; o pacote LSP precisa de uma
implementação de observador de arquivos para enviar mudanças externas. Quando
ela não estiver disponível, reinicie o SLS após alterar módulos fora do editor.
Renomeação sempre relê o disco, independentemente desse observador.

### Bibliotecas do projeto

O SLS também lê o mapa da geração ativa de `santafé instale`. Ele verifica
SHA-256 do mapa e dos módulos Fé antes de analisar; nunca instala, compila ou
executa uma dependência. As definições apontam para o fonte instalado em
`.santafe/geracoes/`. Esse fonte é imutável: o SLS recusa renomeação e formatação
que tentem editá-lo. Atualize a biblioteca pela sua fonte/versão de origem.
As extensões observam também `.santafe/estado.json` para invalidar o mapa.
Não há descoberta de API executando uma biblioteca C; o catálogo de API pública
e eventuais wrappers Fé continuam sendo as fontes de ajuda estática.

O inicializador usa `santafé -P` para não ativar o carregador executável do
projeto no processo de análise. O suporte de leitura/hash é uma biblioteca
privada instalada junto das ferramentas, não um módulo baixado do workspace.

## Limites atuais

A análise não executa expressões, configuração de workspace, bibliotecas C/Fé
nem builds. Metatabelas, exports calculados e destinos obtidos em execução não
são inferidos com certeza. Depuração por DAP e um servidor dedicado de HTML/JS
não fazem parte deste contrato. O suporte nativo desta revisão é POSIX (macOS e
Linux); Windows não foi implementado/homologado e não deve ser anunciado.

Importações literais procuram `.fé`, `.fe`, `/ini.fé` e `/ini.fe` a partir da
pasta do documento, da raiz selecionada e de `bibs/bibf`. Até 16 raízes são
isoladas. A raiz é fixada por descritor na inicialização; componentes internos
são abertos sem seguir links simbólicos, e apenas arquivos regulares são lidos.
O índice considera fontes fechados também; ignora diretórios ocultos,
`node_modules`, `dist`, `build` e `construcao`. Não busca fora das raízes.

## Segurança e capacidade

Cada quadro LSP é limitado a 16 MiB; cada documento a 4 MiB e 100.000 linhas.
Há no máximo 64 documentos e 16 MiB de texto confirmado aberto. Cada lote
admite 256 alterações e até 64 MiB de texto acumulado a reindexar. Estes são
limites de entrada/trabalho, não um teto de memória total do processo (tokens,
mapas, JSON e cópias temporárias também consomem memória).
O cache de fontes do projeto admite 512 arquivos/16 MiB, cada arquivo com até
4 MiB. A enumeração admite 20.000 entradas, 1.024 diretórios e profundidade 32.
Índice incompleto não autoriza uma renomeação parcial. A análise limita tokens,
profundidade e passos. A fila de protocolo admite 256 quadros/32 MiB.

Durante pedidos semânticos, um gancho recolhe novos quadros e cancelamentos;
trabalho Fé é interrompido cooperativamente, com orçamento de 2 segundos de
CPU por pedido. Etapas C são limitadas na entrada, mas não são preemptíveis.
O gancho também controla 256 MiB de objetos Lua vivos após coleta; não é um
limite rígido de RSS ou do alocador do sistema. Gerações grandes descartadas
são coletadas antes de reconstruir o índice para reduzir o pico de memória.
Cancelamento devolve `-32800`; orçamento excedido devolve `-32803` e invalida
caches incompletos. Não existe garantia de tempo real. Fechar um documento
libera seu espelho; um arquivo salvo pode voltar ao cache limitado do projeto.
Medição local em macOS Intel, 100 módulos/3.000 funções e documento de 1.501
linhas: p95 de 27,95 ms para edição/diagnóstico, 0,80 ms para hover e 266,39 ms
para símbolos do projeto (inclui primeira indexação). RSS observado ficou
abaixo de 236 MiB no ensaio de reabertura; não é promessa universal nem prova
isolada de ausência de vazamentos. Linux e inspeção visual são gates separados.

Debian 12, 2 CPUs lógicas, mesmo projeto de 100 módulos: p95 de 79,17 ms para
edição/diagnóstico, 1,15 ms para hover, 227,55 ms para tokens semânticos e
567,95 ms para símbolos do projeto (inclui índice frio). Após aquecimento,
quatro ciclos de abrir/fechar estabilizaram em 107.296 KiB de RSS. São medições
da árvore auditada em 21/10/2026, não garantias para qualquer máquina/projeto.

## Regressão e evolução

```bash
python3 testes/integracao/testar_sls_infraestrutura.py
python3 testes/integracao/testar_sls_incremental.py
python3 testes/integracao/testar_sls_semantica.py
python3 testes/integracao/testar_sls_cancelamento.py
python3 testes/integracao/testar_sls_aceitacao.py --perfil atual
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 \
  --relatorio /tmp/sls-contrato-1.0.json
```

Os 39 critérios principais do alvo 1.0 passaram nesta árvore de desenvolvimento.
Isso não libera 1.0: consulte as evidências separadas dos gates de instalação,
distribuição, escala e hosts reais. Não confundir candidato local com publicação.
