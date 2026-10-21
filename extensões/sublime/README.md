# Santafé para Sublime Text

Pacote 1.1.0 para Sublime Text 4 (build 4107 ou superior), disponível no portal oficial.

Integra o SLS 1.0.0 pelo cliente LSP do Sublime: recursos semânticos são
negociados por sessão e substituem os provedores locais equivalentes sem
duplicação. O iniciador do SLS usa `-E -P`, sem executar fontes/dependências
do projeto. Atualize núcleo 2.1.0 e SLS juntos. As notas 1.0.13 abaixo são
históricas; a homologação visual desta revisão é um gate separado.

Ele reconhece `.fé` e `.fe`, aplica realce de sintaxe, oferece snippets,
conclusões da linguagem e da API pública, exibe ajuda curta ao repousar o mouse
sobre uma função conhecida, indenta estruturas de bloco e integra execução e
verificação sintática no menu **Tools → Build System**.

Depois de escrever um cabeçalho completo, por exemplo
`para índice = 1, 10 início`, pressione Enter para abrir o corpo já fechado
por `fim`. Os snippets continuam disponíveis ao escolher uma conclusão ou usar
Tab sobre o gatilho `para`, `se` ou `função`.

## Gabaritos, HTML e JavaScript

### Cores e cobertura da API — 1.0.13

O realce usa o catálogo público C/Fé das conclusões (610 entradas nesta versão).
Chamadas com nomes locais/aliases também são reconhecidas sintaticamente; não
há execução de imports nem resolução de tipos. No Monokai, `função` é ciano e
itálico, tanto na declaração nomeada como na função anônima.

Use **Santafé: Paleta de HTML e JavaScript embutidos** na paleta de comandos:
acompanhar o tema (padrão) ou paleta suave. A opção `paleta_embutida` no arquivo
`Santafe.sublime-settings` aceita `tema` e `suave`. Apenas os colares HTML/JS da
Santafé mudam; arquivos HTML/JS independentes conservam o tema.
As regras acompanham os esquemas nativos Monokai, Mariana, Celeste, Breakers e
Sixteen. Esquemas de terceiros precisam das regras `meta.santafe-soft-*` e da
regra transparente `meta.santafe-embedded`; se ausentes, o realce básico permanece.

O gerador `extensões/gerar_realce_api.py` mantém as gramáticas alinhadas ao
catálogo. `extensões/gerar_paletas.py` gera as paletas equivalentes dos editores.

Gabaritos entre acentos graves realçam `®nome`, `Ⓡnome` e `®{expressão}`,
inclusive em atributos HTML e strings JavaScript. Chaves aninhadas são
balanceadas; `®nome`, `Ⓡnome` e os delimitadores `®{`, `Ⓡ{` e `}` são laranja,
sem itálico. O interior das chaves é código Santafé, sem herdar a cor do colar.
Sequências como
`\®` permanecem literais. Na revisão em desenvolvimento, `®variável` e
`Ⓡíndice` também aceitam acentos compostos (NFC) e combinados (NFD), inclusive
em HTML/JS. O nome começa com letra Unicode ou `_` e continua com letras,
marcas combinantes, números ou `_`. O marcador e o nome inteiro mantêm o estilo
laranja, sem itálico. Não há normalização automática: declaração e referência
precisam usar a mesma sequência Unicode. A correção requer também o núcleo
corrigido; nas versões publicadas, use `®{índice}`/`Ⓡ{índice}` como alternativa.

HTML é reconhecido por tags, comentários HTML ou `<!DOCTYPE`/`<!doctype>` na
linha do delimitador, inclusive em fragmentos como `[[ | Site</title>]]`.
A procura não ultrapassa o delimitador do colar. JavaScript usa `/* javascript */` ou `/* js */` no início
do conteúdo. Para conteúdo que começa na linha seguinte, anote assim:

```santafé
local página = --[[html]] [[
<h1>Olá!</h1>
<script>const total = 3;</script>
]]
local programa = --[[javascript]] [[
const saudação = "Olá!";
console.log(saudação);
]]
local modelo = `<h1 class="®nome">®{tamanho(nome)}</h1>`
```

As anotações são comentários válidos do Santafé; não mudam o conteúdo do colar
nem o núcleo. Colares longos evitam escapar aspas. O realce usa as gramáticas
HTML/JS do editor, sem acrescentar diagnósticos ou conclusões semânticas dessas
linguagens. Aspas e colchetes continuam sem interpolação de variáveis.

Desde 1.0.12, atributos HTML e comentários JavaScript mantêm seu contexto
mesmo quando uma concatenação os interrompe:

```santafé
local página = [[<a title="Olá, ]] .. nome .. [[!">Abrir</a>]]
local código = --[[javascript]] [[/* início ]] .. nome .. [[ fim */ const n = 3;]]
```

O pacote recorta os literais e entrega um documento virtual às gramáticas
nativas do Sublime. Apenas o conteúdo literal recebe as cores resultantes;
`.. nome ..`, delimitadores e curingas conservam o realce Santafé. Os operandos
dinâmicos são espaços reservados, não são avaliados. Não exige Node, LSP,
execução do programa, leitura de imports nem conexão de rede.

A camada usa regiões de primeiro plano do editor, sem substituir os escopos
da gramática Santafé. Monokai, Mariana, Celeste, Breakers e Sixteen recebem
automaticamente a regra de fundo transparente necessária. Em um esquema de
cores personalizado, adicione esta regra à lista `rules` de **Preferences →
Customize Color Scheme**, preservando as demais regras:

```json
{"scope": "meta.santafe-embedded", "background": "#00000001"}
```

Sem essa regra, o realce básico permanece, mas a camada de continuidade não é
aplicada. Para limitar o trabalho durante a edição, ela também preserva apenas
o realce básico em documentos acima de 400.000 caracteres; trechos virtuais
com linhas acima de 20.000 caracteres são ignorados. A tokenização nativa tem
orçamento de dois segundos, verificado entre lotes (não interrompe uma chamada
interna do Sublime). O recortador limita aninhamentos a 64 níveis. Alterações
obsoletas são descartadas e as cores são recalculadas após 250 ms sem edição.

## Instalação recomendada: Package Control

No Sublime Text, abra a Paleta de Comandos (`Ctrl+Shift+P` ou `⌘⇧P`) e execute
**Package Control: Add Repository**. Informe uma única vez:

`https://xn--santaf-gva.dev.br/est%C3%A1tico/sublime/packages.json`

Depois execute **Package Control: Install Package** e procure por
**Santafe**. As próximas versões serão oferecidas pelo próprio Package
Control, sem copiar arquivos manualmente.

## Instalação manual

Se o Package Control não estiver disponível, baixe `Santafe.sublime-package`
e copie-o para o diretório **Installed Packages** aberto por **Preferences →
Browse Packages…** (suba um nível, se necessário). Reinicie o Sublime Text ou
abra esse diretório novamente para ele recarregar o pacote.

Abra um arquivo `.fé`. O seletor de sintaxe, no canto inferior direito, deve
mostrar **Santafé**. As conclusões surgem enquanto você escreve; use
`Ctrl+Espaço` quando quiser chamá-las manualmente.

O sistema de build usa `santafé` e a variante **Verificar sintaxe** usa
`santafec -p`. Portanto o núcleo precisa estar disponível no `PATH` do Sublime
Text.

## Diagnósticos do SLS

Depois de instalar o núcleo Santafé, abra a Paleta de Comandos e execute
**Santafé: Ativar diagnósticos SLS**. A extensão encontra o iniciador instalado,
grava a configuração do servidor e pede ao Package Control o cliente comunitário
**LSP**. Reabra o Sublime Text uma vez para concluir a instalação. Não é preciso
editar preferências nem ajustar o `PATH` gráfico do macOS.

O SLS 0.1.1 publicado diagnostica sintaxe. O perfil 0.2.0-dev.1 deste fonte
acrescenta intervalos precisos e sincronização incremental, mas exige recompilar
e instalar núcleo e SLS juntos; os binários 2.0.3 publicados não têm a nova API.
Conclusões semânticas entre arquivos, referências, formatação e depuração são
evoluções futuras do servidor.

## Catálogo público

Além do repositório oficial do Santafé, a distribuição contém uma exportação
limpa em `dist/github/`, pronta para um repositório público independente e a
submissão posterior ao catálogo geral do Package Control. Essa via elimina até
o único cadastro inicial de repositório para quem usa o catálogo padrão.
