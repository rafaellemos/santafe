# Contrato de dados da Santafé 3.0

A Santafé 3.0 define listas nativas, nulo armazenável e ONFÉ, com IBA 3. A migração da geração 2 exige revisão dos fontes e recompilação das bibliotecas C. Os cabeçalhos adotam o contrato 3 por padrão, sem opção experimental.

## Decisões consolidadas

- `{}` continua sendo **tabela**, com chaves textuais, numéricas e demais chaves admitidas pelo núcleo. Uma tabela esparsa não vira lista.
- `[]` constrói **lista**, indexada a partir de 1. Listas podem conter outras listas, tabelas e nulos.
- `nulo` é um valor armazenável. Atribuir `t.campo = nulo` conserva a associação; não a apaga.
- Não há novos valores públicos `inexistente`, `indefinido` ou `removido`. Ausência é uma condição consultável, não um valor de domínio adicional.
- Um acento grave delimita gabaritos com `®` e `Ⓡ`; `[=[...]=]`, `[==[...]==]` e níveis superiores delimitam colares brutos. Mantêm-se colares entre aspas e comentários `--`, `--[[...]]` e suas variantes com `=`. Funções continuam usando `função ... fim`; não se introduz `=>`.
- `.onfé` contém dados, não um programa. Sua leitura não executa funções, importações, interpolação ou expressões.

```santafé
local pessoa = { nome = "José", telefone = nulo }
local pedidos = [pessoa, nulo, { número = 42 }]
local bruto = [=[®nome permanece literal; \n também]=]
local nome = "José"
mostre(`Olá, ®nome! Quantidade: Ⓡ{#pedidos}`)
```

## Presença e exclusão

As funções de presença e exclusão são `tabela.temChave(t, chave)` e `tabela.apague(t, chave)`.

| Operação | Resultado |
| --- | --- |
| `t.a = nulo` | Cria ou conserva a chave `a` com valor nulo |
| `t.a` e `t.ausente` | Podem ambos retornar nulo |
| `tabela.temChave(t, "a")` | Consulta a associação própria, sem `__índice` |
| `tabela.apague(t, "a")` | Apaga explicitamente; retorna se existia |
| `pares(t)` | Inclui associações cujo valor é nulo |

`local x` continua inicializando `x` com nulo. Não se introduz exclusão de variável lexical nem erro novo por leitura de global ausente. Nulo permanece falso em condições e compara como nulo independentemente de sua representação interna.

`__índice` só atende ausência: nulo presente impede a busca herdada. `__novoÍndice` só intercepta associação ausente. Um metamétodo com valor nulo permanece desativado. A operação explícita de apagar não simula uma atribuição e não chama esses metamétodos.

## Listas e limites

O comprimento lógico inclui posições nulas e é obtido em tempo constante por `#lista` e `tamanho(lista)`. `ipares` percorre todas as posições, inclusive nulas. Tabelas conservam a regra de fronteira de sequência de `#`, não contagem de chaves; colares conservam a distinção entre grafemas e octetos.

Regras das listas:

- Atualizar `1..n` conserva o comprimento; escrever em `n+1` acrescenta uma posição.
- Escrever além de `n+1` dá erro antes de modificar a lista: não preenche buracos nem aloca pelo maior índice arbitrário.
- Ler um inteiro positivo além de `n` retorna nulo; `temChave` retorna falso.
- Índices textuais, negativos, zero, não finitos ou fracionários são recusados. `1.0` é numericamente o índice 1, mas `"1"` não é.
- `tabela.insira` insere; `tabela.remova` remove e devolve o elemento. `tabela.apague(lista, i)` remove e devolve um lógico. Remoções compactam as posições seguintes.
- Atribuir nulo a uma posição não compacta a lista.
- Listas não aceitam metatabelas. A extensão futura dessa capacidade precisa preservar os invariantes acima.

Na implementação 3.0, o armazenamento de lista reutiliza o arranjo interno de tabela com marca e comprimento próprios, não uma tabela distinguida por heurística JSON. `tipo` distingue os dois; a IBA 3 ainda os representa como `LUA_TTABLE`, oferecendo `lua_islist` e `lua_createlist`. O carregador dinâmico exige o descritor `SANTAFE_MODULE_ABI` dos módulos recompilados. Não aceita bibliotecas instaladas de outra IBA. O contrato e os limites estão em `experimentos/dados-v10/IBA.md`.

## Colares brutos e migração léxica

Decisão reafirmada em 24/10/2026: manter o contrato dados.8. Não restaurar
`[[...]]` como colar nem exigir espaços entre aberturas de listas aninhadas.
`[[1,2],[3,4]]` e `[ [1,2], [3,4] ]` representam a mesma lista de listas.
Os delimitadores brutos com `=` preservam essa sintaxe herdada do Lua;
isso não significa compatibilidade com os antigos colares `[[...]]`, que
continuam exigindo a migração descrita abaixo.

Colares brutos exigem pelo menos um `=` na abertura: `[=[` fecha com `]=]`, `[==[` fecha com `]==]`, e assim por diante. Somente um fechamento com exatamente a mesma quantidade de `=` encerra o colar. O conteúdo não é aninhado. Para incluir um fechamento, escolha outro nível; acentos graves isolados ou duplos dentro do bruto são texto literal. `[=[]=]` é um bruto vazio.

Não há escapes nem interpolação em colares brutos. As quebras CRLF e CR são normalizadas para LF pelo lexer. Uma quebra imediatamente após a abertura é descartada, preservando a semântica dos colares longos estáveis. Para guardar uma quebra inicial, escreva duas. A migração a partir de dados.7 acrescenta essa quebra de proteção quando necessário.

`[[...]]` deixa de ser colar: `[[1,2],[3,4]]` é uma lista de listas. `[=[...]=]` e níveis maiores conservam sua semântica estável. Comentários longos não mudam. O migrador estável usa os lexemas do núcleo **estável**, converte somente os antigos colares `[[...]]` e conserva os níveis já válidos com `=`. O migrador de dados.7 usa o lexer daquele candidato para converter somente colares brutos com dois acentos graves. Nenhum migrador executa o programa recebido ou modifica o arquivo de entrada. Comentários e colares entre aspas não são transformados por busca textual.

Dois acentos graves consecutivos voltam a representar um gabarito vazio; não são delimitadores de bruto. ONFÉ não admite gabaritos, nem vazios. Construções antigas como `[[1]]` são ambíguas: podem compilar na geração 3 com outro significado. Por isso, nunca se deve testar compatibilidade apenas verificando se o código compila.

## ONFÉ

Exemplo de arquivo:

```santafé
{
    pessoa = { nome = "José", telefone = nulo },
    lista = [1, 2, nulo, 4],
    vazia = [],
    tabelaVazia = {},
    mapa = { [1] = "um", ["1"] = "chave textual" },
}
```

O parser admite raiz escalar ou composta, vírgula final, comentários, identificadores Unicode e chaves literais textuais, numéricas ou lógicas entre colchetes. Rejeita chaves duplicadas, código, gabaritos, ciclos na serialização, objetos com metatabela, números não finitos e tipos executáveis/opacos. A raiz e os valores podem ser nulos; chaves não podem.

Limites de ONFÉ: entrada/saída de até 4 MiB, profundidade até 64 e até 200 mil lexemas, sujeitos também ao limite interno do lexer. O parser não usa `carregue` nem `executeArquivo` sobre o conteúdo. O programa importa o módulo ONFÉ; o arquivo de dados nunca carrega código.

API: `onfé.decod`, `onfé.cod`, `onfé.carregue`, `onfé.paraJSON`, `onfé.deJSON`, `onfé.grave` e `onfé.graveAssíncrono`. A persistência atômica e seus limites estão documentados em `experimentos/dados-v7/PERSISTENCIA.md`. O codificador pode emitir colares entre aspas: preserva o valor, não a formatação original dos delimitadores.

## Ponte JSON e decisões reservadas

JSON comum representa listas como arrays, tabelas de chaves textuais como objetos e nulo como `null`. `[]`, `{}` e associações nulas sobrevivem à ida e volta. A conversão recusa chaves numéricas/lógicas de tabelas ao gerar JSON comum, em vez de produzir silenciosamente nomes duplicados. A leitura JSON também recusa nomes duplicados.

A proposta anterior de converter automaticamente chaves textuais formadas por números **não está aplicada**: `"1"` e `1` permanecem distintos, preservando os dados existentes. Essa política exige homologação explícita antes de uma migração destrutiva; nomes com zeros iniciais e inteiros grandes agravam a ambiguidade.

ONFÉ conserva chaves numéricas sem restrição artificial imposta pelo JSON. O transporte JSON etiquetado, versionado e sem colisões com campos comuns foi projetado, mas não faz parte deste primeiro executável: a ponte atualmente oferecida é apenas JSON comum, com recusa explícita quando não puder representar as chaves. Inteiros de 64 bits são emitidos e lidos sem passar por `double` neste núcleo; consumidores JavaScript ainda precisam cuidar de inteiros maiores que sua faixa exata.

A forma `{var}` continua com a semântica anterior nesta versão. Não foi reinterpretada silenciosamente como `{var=nulo}`. A migração de construtores posicionais para `[]` precisa de análise de intenção; tabelas numéricas legítimas continuam existindo.

## Integração e migração

O SLS 1.1 analisa a sintaxe da geração 3 e arquivos ONFÉ sem executar seu
conteúdo. Operações de código não se aplicam a ONFÉ. O aviso opcional de nomes
sem declaração local não cria `temVar` nem muda a leitura de globais dinâmicos.
As extensões compatíveis para VS Code e Sublime compartilham esse SLS e
oferecem realce de HTML/JS embutidos com paleta suave.

A migração exige revisão de atribuições nulas, construtores posicionais,
metatabelas, bancos, caches e bibliotecas C, além da transformação léxica dos
colares antigos. Uma compilação bem-sucedida, sozinha, não prova equivalência.
A atualização operacional preserva dados, prepara uma cópia atual do código
e possui reversão; essa reversão não desfaz mensagens ou dados novos.

Listas permanecem sem metatabelas nesta versão. Uma tabela com metatabela
pode conter listas. A persistência atômica e seus limites estão detalhados
no manual e em `experimentos/dados-v7/PERSISTENCIA.md`.

Os relatórios registram os ensaios efetivamente executados e suas limitações.
A preparação de artefatos não significa publicação no servidor ou nos
catálogos dos editores; a distribuição só muda após a publicação explícita.
