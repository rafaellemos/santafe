# Candidato dados.3 — 23/10/2026

Resultado: candidato isolado aprovado na bateria abaixo, não liberado como
versão maior estável. Nenhuma instalação, reinício de serviço, alteração de
banco empresarial, publicação de catálogo, push ou etiqueta foi realizada.

## Correções implementadas

- Exclusões reais de caches, conexões, filas e campos temporários usam
  `tabela.apague`, sem converter indiscriminadamente toda atribuição nula.
- PULSO preserva listas, nulos e objetos aninhados; protege campos sigilosos,
  recusa ciclos e aceita referências compartilhadas não circulares.
- Fronteiras postais conhecidas como sequências usam adaptação explícita e
  validada. Tabelas esparsas/mistas não são convertidas silenciosamente.
- Linhas MariaDB, diretas e preparadas, são listas e preservam NULL inicial,
  intermediário e final. EOF continua distinto de uma linha contendo nulos.
- Resultados sequenciais de DNS e do lexer usam listas. Registros continuam
  tabelas. O SLS e seu corpus foram ajustados à nova representação.
- Cinco módulos C recompilados: arquivo, rede, mariadb, segredo e tomada.
  Barreira de ABI experimental recusa módulos antigos que usam a verificação
  padrão `luaL_checkversion`/`luaL_newlib`. Isso não é uma barreira universal
  para código nativo de terceiros que ignore essas verificações.
- Hash do SLS estático também funciona no Debian com OpenSSL. A compilação
  WebAssembly tem opt-in experimental, sem mudar o modo público por padrão.
- Migração léxica feita pelo núcleo estável em árvore separada; substituições
  semânticas explícitas ficam registradas em `MIGRACAO.json`. Fixtures de teste
  foram adaptadas às novas regras sem retirar verificações.

## Ensaios executados

| Bateria | macOS Intel | Debian 12 x86-64 |
| --- | --- | --- |
| Bibliotecas C/Fé | 76 aprovados, 11 separados por exigir banco | 76 aprovados, 11 separados por exigir banco |
| MariaDB temporário próprio | 12 aprovados | 12 aprovados |
| Fronteiras PULSO/JSON | aprovado | aprovado |
| Módulo C antigo recusado / novo aceito | aprovado | aprovado |
| SLS adversarial/incremental | 39 aprovados | 39 aprovados |
| Aceitação LSP perfil 1.0 | 39 aprovados | 39 aprovados |
| Núcleo, ONFÉ e migração cruzada | 10 aprovados com ASan/UBSan | 7 ensaios independentes do controle estável aprovados |
| API C experimental | aprovada com ASan/UBSan | aprovada |
| SLS com ASan/UBSan | 39 aprovados | não executado com sanitizadores |

Os 12 testes SQL abrangem os 11 separados da primeira bateria e mais o teste
específico de NULL. Não contar os testes ignorados como aprovados antes disso.
Incluem autenticação, filas, IMAP/COPY/APPEND, conversas, quarentena e recuperação
de reservas expiradas, sempre com dados de ensaio. As instâncias temporárias
foram paradas pelos respectivos controladores.

Núcleo/ONFÉ: 500 conversões determinísticas JSON → ONFÉ → JSON, limites,
recusa de execução, inteiros de 64 bits, chaves duplicadas, mutações densas,
nulos, coleta de lixo, índices inválidos e invariantes de metatabelas.
Os três ensaios adicionais no Mac comparam migração, bytecode e controle
estável. Não foram declarados como repetidos no Debian.

WebAssembly: compilado no Debian com Emscripten 6.0.12 e testado no Node 24.19.0:
15 casos aprovados mais recuperação após erro. Inclui listas, nulos, Unicode
composto/combinado, ONFÉ, JSON e distinção entre `\n` literal e quebra real.
Cache de compilação privado em `/tmp`; executor do portal não substituído.

ASan/UBSan: 10 testes de núcleo + 39 de SLS e ensaio C sem ocorrência reportada;
interrupção no primeiro erro habilitada. LeakSanitizer desativado no macOS;
portanto não se declara auditoria de vazamentos por essa ferramenta.

## Evidência e integridade

A árvore final ensaiada localmente foi `/tmp/santafe-dados3-wfd440ch`; no
Debian, `/tmp/santafe-dados3.FbzAgzGF/final`. Os logs/JSON foram preservados em
`evidencias/` em cada árvore. Pacote de fontes ensaiado, antes da atualização
documental e do iniciador de conveniência:

`d4b04c0b7b1d50a7908ea173fe5b4ac6f252f8e75aa8dbec0226d00cff397d6d`

O pacote de entrega tem manifesto próprio. As mudanças posteriores à bateria
são documentação e `experimentar.sh`, cujo exemplo e testes são repetidos.
Os hashes das fontes de implementação devem permanecer iguais aos ensaiados.
Uma tentativa anterior de empacotamento simultâneo à compilação foi abortada
por arquivo temporário do compilador; esse arquivo parcial não é distribuído.

## Ainda não homologado

- Migração integral e testes ponta a ponta dos aplicativos, gerenciador de
  bibliotecas, catálogo, publicadores e manual público.
- Windows, macOS ARM, ABI/bytecode definitivo da próxima versão maior,
  dependências nativas de terceiros e caminhos de atualização/rollback reais.
- Desempenho/carga prolongada, falhas de alocação sistemáticas e auditoria
  completa de persistência/atomicidade do ONFÉ.
- Nova inspeção visual dos dois editores e do navegador com este pacote.
  A validação anterior de dados.2 não foi reclassificada como teste visual
  de dados.3. O teste LSP não substitui essa inspeção.
- As listas ainda não aceitam metatabelas; não foi anunciado suporte novo.

Próxima etapa: migrar e ensaiar a cadeia de ferramentas/aplicativos em ambiente
paralelo, fechar os itens de compatibilidade e só então preparar uma proposta
de versão maior estável com publicação reversível autorizada.
