# Santafé para Visual Studio Code

Extensão Santafé 1.1.0, disponível no portal oficial, para arquivos (`.fé` e `.fe`). Ela oferece:

- reconhecimento de arquivos, comentários, pares e indentação;
- realce de sintaxe, trechos e ícone próprio;
- conclusões para a linguagem, bibliotecas, funções globais, API pública e
  símbolos declarados no arquivo atual;
- ajuda ao passar o mouse, estrutura de funções no explorador e navegação para
  funções declaradas no arquivo atual;
- diagnósticos e provedores semânticos através do SLS 1.0.0: referências,
  renomeação, ajuda de parâmetros, símbolos, recuo e navegação entre módulos.

Os recursos são negociados com o servidor, com fallback local quando ausentes.
O SLS não executa o fonte nem suas dependências; a inicialização automática usa
`-E -P`. Atualize núcleo 2.1.0 e SLS juntos. Não requer um servidor SLS diferente
do usado pelo Sublime. As notas 1.0.x abaixo descrevem recursos preservados.

Salve o arquivo com a extensão `.fé` ou `.fe` — ou escolha **Santafé** no
seletor de linguagem do canto inferior direito — para ativar esses recursos.

## Instalação

### Marca oficial — 1.0.7

O ícone passa a usar o cordeiro oficial do portal Santafé. Esta revisão corrige
somente a identidade visual; realce, conclusões, paletas e integração SLS
permanecem iguais aos da versão 1.0.6.

### Cores e cobertura da API — 1.0.6

O realce usa o mesmo catálogo C/Fé das conclusões (610 entradas nesta versão).
Chamadas com nomes definidos pelo usuário, inclusive aliases de bibliotecas,
também são realçadas como chamadas. Isso é classificação sintática, não resolução
de tipos/importações nem garantia de que uma função exista em execução.

Na paleta de comandos, escolha **Santafé: Paleta de HTML e JavaScript embutidos**:
`tema` mantém as cores do editor (padrão); `suave` aplica uma paleta menos saturada
somente ao conteúdo HTML/JS dos colares. Também há a configuração
`santafe.highlight.embeddedPalette`. Arquivos `.html`/`.js` não são alterados.
As paletas têm variantes para fundo claro/escuro.

Os marcadores `®var`/`Ⓡvar`, as chaves externas de `®{…}`/`Ⓡ{…}` e nomes de
métodos após `:` são laranja, sem itálico. Dentro das chaves, continua o realce
Santafé: colares internos são colares, números são números. No perfil Monokai,
`função` é ciano e itálico. Não são gravadas preferências sem uma escolha na
paleta; as decorações visuais são removidas ao desativar a extensão.

Para regenerar as regras a partir do fonte, execute na raiz do repositório:
`python3 extensões/gerar_embutidos.py`, `python3 extensões/gerar_realce_api.py` e
`python3 extensões/gerar_paletas.py`, nesta ordem.

O SLS é um processo local. Instale o núcleo Santafé na mesma máquina onde o
VS Code está rodando, de forma que `santafé-sls` esteja no `PATH`. Em uma sessão
Remote SSH, esse comando deve estar instalado no host remoto da extensão.

Ao abrir o próprio repositório Santafé, a extensão encontra automaticamente
`src/santafé` e `ferramentas/sls/sls.fé`. Basta compilar o núcleo:

```sh
make cbin
```

Para trabalhar em qualquer outro projeto, instale o inicializador global:

```sh
sudo make install
```

Gere o pacote sem depender de Node.js:

```sh
python3 empacotar.py
code --install-extension dist/santafe-1.1.0.vsix
```

Também é possível escolher **Instalar do VSIX...** na visualização Extensions do
VS Code e selecionar o arquivo gerado.

## Configuração

Por padrão a extensão executa:

```text
santafé-sls
```

Para apontar a outra instalação, defina `santafe.languageServer.command` nas
configurações do VS Code. `santafe.languageServer.args` acrescenta argumentos
ao comando. Use `santafe.languageServer.trace` para inspecionar os quadros LSP
em **Saída → Santafé SLS**.

## Gabaritos, HTML e JavaScript

O realce distingue `®nome`, `Ⓡnome` e `®{expressão}` nos gabaritos entre
acentos graves. Chaves aninhadas são balanceadas; `\®` permanece literal.
O curinga integra o realce de `®nome`; `®{` e `}` recebem o estilo de operador,
enquanto o conteúdo da expressão mantém seu próprio realce.
Colares com aspas ou colchetes não passam a interpolar por serem realçados.
Desde a versão 1.1.0, a forma curta também reconhece `®variável`,
`Ⓡíndice` e acentos combinados (NFD), sem cortar o nome no acento. O nome começa
com letra Unicode ou `_`; em seguida aceita letras, marcas combinantes, números
e `_`. O curinga inteiro mantém a cor laranja e o estilo normal, inclusive em
HTML/JS. Não há normalização: declaração e referência precisam usar a mesma
sequência Unicode. Essa forma requer o núcleo Santafé 2.1.0 ou posterior;
em núcleos anteriores, use `®{índice}`/`Ⓡ{índice}` como alternativa.

HTML é reconhecido por uma tag, comentário HTML ou `<!DOCTYPE`/`<!doctype>`
na linha de abertura, inclusive depois de texto como `[[ | Site</title>]]`.
A procura não ultrapassa o delimitador do colar. JavaScript é reconhecido pelo comentário
inicial `/* javascript */` (ou `/* js */`). Para começar na linha seguinte,
coloque a anotação `--[[html]]` ou `--[[javascript]]` antes do delimitador,
na mesma linha:

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

São comentários válidos do Santafé, não uma nova sintaxe do núcleo. Use colares
longos para não precisar escapar aspas. O recurso fornece **realce**, não
diagnósticos ou autocompletar semântico de HTML/JS. O SLS continua verificando
o programa Santafé, sem executar o conteúdo dos colares.

## Concatenações e realce embutido

A versão 1.0.5 delimita os colares Santafé antes de realçar HTML/JS. Assim,
atributos e comentários podem continuar após `.. expressão ..`, sem capturar
o código intermediário nem o código depois do colar:

```santafé
local html = [[<b class="prefixo-]] .. nome .. [[-final">Olá</b>]]
local js = --[[javascript]] [[/* início ]] .. nome .. [[ final */ const n=1;]]
```

O contexto é preservado dentro da mesma expressão concatenada, não entre
atribuições ou funções distintas. Expressões dinâmicas são espaços reservados:
o editor não executa o programa nem adivinha tags/aspas que elas produziriam.
As gramáticas HTML/JS/CSS são as nativas do editor; o runtime acompanha o VSIX.
Não é necessário instalar Node, bibliotecas ou outro servidor de linguagem.

As cores são aplicadas pela API pública de tokens semânticos do VS Code,
mas o recurso é **léxico**, independente do SLS. A configuração de linguagem
habilita `editor.semanticHighlighting.enabled`; se o usuário desabilitá-la,
o texto conserva o realce básico Santafé, com delimitadores corretos.
O mesmo fallback vale para documentos acima de 1.000.000 unidades UTF-16,
expressões com profundidade acima de 128, linhas virtuais acima de 20.000
unidades ou tokenização que exceda o orçamento de tempo. Limites do realce não
restringem o compilador. Espaços de trabalho não confiáveis conservam somente
o TextMate, pois esta extensão exige confiança para ativar suas funcionalidades.

## SLS

O SLS 1.0.0, publicado com o núcleo Santafé 2.1.0, oferece diagnósticos com
intervalos precisos, sincronização incremental, conclusões, ajuda de parâmetros,
definições e referências, renomeação com verificação de escopo e formatação
conservadora do recuo. Analisa importações estáticas sem executar o programa nem
suas dependências. Não oferece inferência completa de tipos nem depuração de
execução; análise sintática e indexação ainda percorrem o documento completo.

Quando o servidor está disponível, a extensão negocia esses recursos pelo LSP.
Sem ele, mantém os provedores locais de conclusão, ajuda e navegação. O realce
de HTML/JS e dos gabaritos continua independente do servidor.
