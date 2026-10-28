# Candidato dados.4 — bateria da cadeia, 23/10/2026

Resultado: aprovado nos ensaios abaixo, ainda **experimental**. Dados.3 e a
instalação estável foram preservados. O exemplo anterior não foi refeito.

## Falhas encontradas e corrigidas no laboratório

O gerenciador do candidato anterior falhava já no primeiro empacotamento:
`autores: lista esperada`. A representação JSON de listas havia mudado, mas
os validadores e alguns produtores ainda esperavam/produziam tabelas.

- Manifestos e listas de arquivos/transações agora usam o tipo lista explícito.
- Codificação canônica distingue `[]`, `{}` e nulo; ordena recursivamente
  as chaves textuais, inclusive nos objetos dentro de listas. Mantém limites,
  recusa ciclos/metatabelas e não converte chaves numéricas em texto.
- O resolvedor apaga efetivamente as marcações temporárias ao retroceder,
  sem deixar chaves nulas presentes na seleção de dependências.
- A ajuda da CLI foi migrada lexicalmente para o novo delimitador bruto.
- O suporte C lista diretórios com listas, informa a ABI experimental e
  verifica a compatibilidade ao carregar. Receitas C explicitamente autorizadas
  recebem a opção de compilação correspondente; a fixture verifica essa ABI.
- O ambiente dos ensaios de pacotes não herda credenciais/caminhos de módulos
  do usuário. Catálogo e HTTPS são locais, com arquivos e CA de teste.
- O ensaio adicional de colares multilinha revelou que JSON aceitava controles
  crus dentro de aspas e ignorava bytes após NUL. O modo experimental agora
  recusa ambos, preservando escapes válidos e espaço/quebras entre os membros.
  Testados os 32 controles em chaves/valores, ida e volta, ONFÉ multilinha e
  a distinção entre quebra real e barra seguida de n. Baterias repetidas após
  essa correção; a aceitação indevida não foi tratada como JSON válido.

As mudanças semânticas em Fé estão apenas na árvore experimental, registradas
em `MIGRACAO-CADEIA.json`. As extensões em `ferramentas/pacotes/nativo.c` são
condicionadas por `SANTAFE_DADOS_EXPERIMENTAL`; a verificação padrão de versão
do módulo também foi adicionada ao modo normal. Um módulo compilado sem a
opção experimental foi carregado no núcleo estável local: manteve retorno
tabela e ausência de `abiDados`. Não houve substituição do binário estável.

## Resultados repetidos nesta rodada

| Bateria | macOS Intel | Debian 12 x86-64 |
| --- | --- | --- |
| Gerenciador: instalação, integridade, recuperação, CLI, HTTPS, catálogo | aprovado | aprovado |
| Fronteiras específicas lista/nulo/canônico/resolvedor | 9 testes aprovados | 9 testes aprovados |
| Suporte nativo: injeção de falhas de alocação | 1.440 cenários aprovados | 1.440 cenários aprovados |
| Lexer/SLS: alocação e entradas arbitrárias | 900 + 3.000 aprovados | 900 + 3.000 aprovados |
| Unicode 17: grafemas | 766 casos / 1.990 fronteiras | 766 casos / 1.990 fronteiras |
| Gabaritos ®/Ⓡ, NFC/NFD, fonte/bytecode | 1.320 nomes aprovados | 1.320 nomes aprovados |
| Datas do Carteiro: UTC, São Paulo, Tóquio | aprovado | aprovado |
| Bibliotecas C/Fé | 76 aprovados, 11 separados para SQL | 76 aprovados, 11 separados para SQL |
| MariaDB temporário próprio | 12 aprovados | 12 aprovados |
| SLS adversarial/incremental | 39 aprovados | 39 aprovados |
| Aceitação LSP perfil 1.0 | 39 aprovados | 39 aprovados |
| Núcleo/ONFÉ e migração cruzada | 10 aprovados | 7 independentes do controle estável |
| Fronteiras PULSO/JSON e módulo C antigo/novo | aprovado | aprovado |
| ONFÉ multilinha, controles JSON crus/escapados e NUL | aprovado | aprovado |

Os dez grupos de `testar-cadeia.py` passaram integralmente nos dois sistemas.
Os números da tabela não devem ser somados como testes unitários homogêneos:
há grupos, cenários de injeção e casos de dados distintos. Os 12 testes SQL
cobrem os 11 separados da bateria geral mais o ensaio de NULL; não são 23.

Testes do gerenciador incluem empacotamento determinístico, catálogo local
imutável, instalação por projeto, importação real, offline, seis fases de
interrupção, preservação de edição manual, confinamento de caminhos, links/FIFO,
travas, permissão explícita para código C e recusa de TLS não confiável.
Compilação controlada não é sandbox para código nativo malicioso autorizado.

Os testes SQL usaram instâncias novas com `--no-defaults`, loopback, socket e
credenciais fictícias próprios. Cobriram autenticação, filas, IMAP/COPY/APPEND,
conversas, quarentena e recuperação. As duas instâncias foram encerradas.
Nenhum banco empresarial ou mensagem real foi lido ou modificado.

No Mac, o suporte nativo de pacotes e o lexer/SLS repetiram os 1.440 e
900 + 3.000 cenários com AddressSanitizer/UndefinedBehaviorSanitizer e parada
no primeiro erro: nenhuma ocorrência reportada. A regressão adicional de
colares/controles JSON também passou com ambos os sanitizadores. Os harnesses conferem seu
heap/descritores; LeakSanitizer ficou desativado, portanto não se declara uma
auditoria universal de vazamentos. Sanitizadores não foram repetidos no Debian.

WebAssembly foi recompilado no Debian com Emscripten 6.0.12 e cache privado.
Node 24.19.0 executou 16 casos mais recuperação após erro, incluindo a regressão
adicional de colares/controles JSON. O harness reutilizado permanece em
`dados-v3/testar-wasm.js`, atualizado na árvore experimental para dados.4.
É um DOM mínimo, não validação visual do navegador.

## Evidências e reprodução

- Mac: `/tmp/santafe-dados4-m_ueggu6/evidencias`.
- Debian: `/tmp/santafe-cadeia4.bNaMhCwY/arvore/evidencias`.
- Sanitizadores: `/tmp/santafe-dados4-asan.IQulsP`.
- Pacote final e cópias dos logs: `dist/candidato-dados-v4`.
- Primeira fonte enviada para a bateria remota, antes da correção de JSON: SHA-256
  `0b5e47ff2c4663d82d5a98add43f33d5d9b439f1078b1887d6a1f48f2032f5a1`.

O pacote final contém a correção JSON e sua regressão, recompiladas/retestadas
nas duas plataformas. A comparação da implementação final contra as árvores
ensaiadas é preservada na entrega. A receita
`preparar.py` parte do arquivo dados.3 com hash fixado e verifica cada alteração;
não deve ser confundida com um instalador.

## Limites e próxima etapa

Esta rodada fecha a migração ensaiada do gerenciador e suas interfaces, não
toda a cadeia de implantação. Ainda faltam homologação integral dos aplicativos,
instalação/atualização/rollback da distribuição, manual público migrado,
Windows/macOS ARM, ABI/bytecode definitivo, carga prolongada, persistência
atômica do ONFÉ e nova inspeção visual dos editores. Listas continuam sem
metatabelas. A barreira ABI não protege contra módulos que ignorem a verificação.

Portanto não há comando de publicação em produção nesta entrega. Nenhum
catálogo público, serviço, Git remoto, etiqueta ou instalação foi alterado.
