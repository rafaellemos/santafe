# Gabaritos Unicode — correção local de 21/10/2026

**Registro histórico da primeira rodada.** As restrições e números abaixo
descrevem aquela rodada, não o estado posterior da publicação conjunta.
Para versões candidatas, Debian/WebAssembly, editores instalados e pendências
atuais, consulte [Lançamento 2.1.0](LANCAMENTO-2.1.0.md),
[auditoria SLS](AUDITORIA-SLS-1.0-20261021.md) e o resultado do conjunto de ensaio.

## Escopo e situação

Correção solicitada para `®variável` e `Ⓡvariável` no núcleo, VS Code e
Sublime. Aplicada no fonte de desenvolvimento; não publicada, instalada,
etiquetada nem enviada ao servidor. Os pacotes de teste mantêm os números das
versões existentes e **não devem substituir os artefatos públicos**; uma
publicação deverá atribuir novas revisões e distribuir também o núcleo.

O trabalho anterior do SLS foi preservado e submetido à regressão. Nenhuma
capacidade nova do SLS foi implementada nesta correção.

## Defeito e correção

- O núcleo classificava bytes isolados com `isalpha`/`isalnum`. Os editores
  restringiam a forma curta a `[A-Za-z_][A-Za-z_0-9]*`. Assim, `®variável`
  podia buscar `vari` e deixar `ável` no texto.
- O núcleo agora decodifica UTF-8 e reconhece `[L_][LMN_]*`: letra ou `_` no
  início; letras, marcas combinantes, números ou `_` na continuação. Usa
  categorias Unicode 17.0.0 versionadas, sem depender do locale. Não inclui
  emoji, pontuação nem o curinga seguinte no nome.
- A gramática e o recortador HTML/JS dos dois editores foram corrigidos,
  incluindo o gerador das gramáticas. O curinga e o nome inteiro mantêm o
  estilo já definido: laranja, sem itálico. Expressões entre chaves continuam
  sendo código Santafé.
- NFC e NFD são aceitos **sem normalização automática**. Declaração e
  referência precisam conservar a mesma sequência de pontos de código.
  Essa correção não muda a identidade dos nomes nem as regras gerais do lexer.
- O teste de carga revelou uma falha adicional na montagem do gabarito:
  um valor intermediário ficava entre o colar convertido e a caixa do
  `luaL_Buffer`. Ao crescer, o buffer podia acessar o objeto errado e derrubar
  o processo. Corrigida a disciplina da pilha nas formas simples e entre
  chaves; o nome temporário também passou a ser gerenciado pelo GC.

Dados oficiais utilizados: [DerivedGeneralCategory.txt, Unicode 17.0.0](https://www.unicode.org/Public/17.0.0/ucd/extracted/DerivedGeneralCategory.txt).
Fonte e licença ficam em `ferramentas/unicode/17.0.0`; a tabela C é regenerada
offline por `ferramentas/gerar_unicode.py`.

## Validação executada

Ambiente: macOS Intel; núcleo recompilado localmente. Todos os ensaios abaixo
passaram após as correções.

| Ensaio | Resultado |
| --- | --- |
| Gabaritos no núcleo | 1.320 nomes, locais/globais, ambos os curingas, fonte e bytecode, locale C |
| NFC/NFD e limites | Nome iniciado por acento, marcas combinadas, números na continuação, escapes, adjacência, NUL e UTF-8 malformado |
| Carga do buffer | 3.000 pares de interpolações simples, 3.000 pares entre chaves e resultado de 100 mil octetos |
| AddressSanitizer e UndefinedBehaviorSanitizer | Gabaritos e bateria Unicode sem diagnóstico; compilação isolada em diretório temporário, sem instalar |
| Unicode já existente | 766 casos oficiais e 1.990 fronteiras de grafemas |
| VS Code, TextMate + HTML/JS | 175 casos; cores nos temas Dark+ e Monokai |
| VS Code, API/paletas | 611 entradas; 20 nomes Unicode × 2 curingas × 3 contextos; limites UTF-16 e decorações |
| Concatenações VS Code | 40 verificações, cancelamento e 3.000 fragmentos |
| Sublime | Regra de interpolação compilada em Oniguruma; recortador Python com 20 nomes × 2 curingas × 3 contextos; 43 casos anteriores e 3.000 fragmentos |
| Pacotes dos editores | Estrutura, empacotamento, conclusões e comportamento automatizado |
| Regressão `testar.sh` | 84 arquivos de teste das bibliotecas, testes adicionais de integração e SLS aprovados |
| Manual | 1.238 IDs, 581 funções colapsáveis, 171 exemplos, 259 contratos C e 344 Fé |
| Geradores e alterações | Tabelas Unicode conferidas e `git diff --check` sem erros |

## Limites da conferência

- Não houve nova inspeção visual das janelas nem execução da gramática no
  `plugin_host` do Sublime. Os testes de recorte, expressões regulares e
  empacotamento são automatizados; não equivalem a um teste visual completo.
- Não foram alteradas as extensões instaladas no computador. Os testes usam
  os fontes corrigidos e pacotes locais.
- Não foram executados nesta rodada Debian, WebAssembly, banco MariaDB real
  nem autenticação postal com DNS real. Os testes condicionais sem ambiente
  configurado permaneceram ignorados, sem serem contados como homologação.
- O ensaio de memória usou ASan/UBSan, sem LeakSanitizer. A compilação opcional
  com `LUA_USE_APICHECK` encontrou dois escapes hexadecimais antigos inválidos
  nas mensagens de `src/lapi.c`; essa opção não foi habilitada no ensaio final
  e não foi alterada nesta tarefa.

Log local da regressão completa:
`/tmp/santafe-gabaritos-unicode-regressao.log`.
