# Candidato dados.8 — revisão dos colares brutos

Data de referência: 23/10/2026. Somente homologação; produção preservada.

## Implementação

O lexer experimental admite novamente `[=[...]=]` e qualquer nível maior com
`=`, mantendo `[[1],[2]]` como lista aninhada. Reutiliza o leitor de colares
longos estável: nenhuma interpolação/escape, normalização CRLF/CR e supressão
de uma quebra imediatamente após a abertura. A quantidade de `=` deve coincidir.
Dois acentos graves não abrem mais bruto; um gabarito vazio continua válido.
`função ... fim` permanece; nenhuma função com seta foi introduzida.

ONFÉ, SLS, kits isolados VS Code/Sublime, realce embutido HTML/JS e extensão
Prism do manual acompanham a alteração. Migradores estável e dados.7 usam os
lexemas reais; preservam o conteúdo, comentários, aspas, quebras iniciais e
fechamentos parcialmente sobrepostos. Os kits são 0.0.8 de laboratório.

## Evidências desta rodada

- macOS Intel: 14 grupos novos de colares/migração, incluindo 100 textos
  aleatórios comparados com o núcleo 2.1.0 e preservação de dados.7.
- 183 fontes Fé de bibliotecas, ferramentas, aplicativos, exemplos e testes
  compilados sem execução. 495 fontes relevantes da reprodução limpa foram
  comparados por hash à árvore macOS ensaiada: nenhuma diferença.
- Regressão local: núcleo, ONFÉ, fronteiras JSON/PULSO, arquivo legado, ABI,
  17 grupos de persistência, 39 testes SLS, conclusões ONFÉ/arquivo, carga
  incremental de 200 edições e instalação/atualização/rollback passaram.
- LSP novo: alterações incrementais de níveis incompatíveis, diagnóstico e
  recuperação em Fé e ONFÉ; rename preserva conteúdo bruto e altera gabaritos.
- Manual: 174 exemplos compilados, 264 contratos C, 351 Fé; 12 exemplos
  seguros executados. Não é execução de todos os exemplos.
- Editores: 25 casos TextMate/HTML/JS anteriores e 45 casos adicionais de
  níveis, Unicode, fechamento e retomada. Sublime: 17 testes de recorte
  anteriores (incluindo 3.000 fragmentos) e sete adicionais passaram.
- Aplicativos completos em macOS: 13 percursos com MariaDB temporário,
  mensagens sintéticas e portas de loopback, incluindo carga concorrente de
  60 segundos. Nada foi lido de bancos empresariais.

- Debian 12 x86_64: os mesmos 14 grupos novos, 183 compilações, regressão
  de 11 etapas (incluindo 17 persistência/39 SLS), LSP incremental e 13
  percursos completos dos aplicativos com carga de 60 segundos passaram.
- WebAssembly recompilado no Debian: 18 casos e recuperação após erro
  passaram. Um fixture ONFÉ interno ainda usava o delimitador anterior;
  foi corrigido e todos os 18 casos repetidos. O log inicial foi preservado.
- macOS adicional: aceitação LSP 39/39; lexer com 900 falhas de alocação e
  3.000 entradas arbitrárias, heap/descritores sem erro; 17 grupos de
  persistência com ASan/UBSan no helper C; cinco testes da regra Prism.
  Sanitizadores não foram aplicados à VM inteira nesta rodada.

## Limites e correções encontradas

As primeiras execuções apontaram fixtures ainda escritas com os delimitadores
anteriores; corrigidas e baterias repetidas, sem omitir os casos. O teste de
migração também precisou respeitar a regra existente do CLI para `-e` iniciado
por comentário. Quatro acentos graves são lexados como dois gabaritos vazios,
não como bruto; a sintaxe histórica não foi alterada para impor uma rejeição nova.

Os ensaios de editor não são inspeção de pixels nem homologação dos hosts
nativos. Nenhum pacote foi instalado nos perfis pessoais; nenhuma versão foi
publicada em Marketplace/Package Control. A execução WASM
usou Node/DOM mínimo, não validação visual de navegador.

Artefatos e evidências: `dist/candidato-dados-v8`. Servidor usado somente em
`/tmp/santafe-dados8.fhLMCQzP`; fontes de ensaio em `arvore`. O pacote final
é separado do pacote preliminar para preservar hashes e rastreabilidade.
Scripts/logs reaproveitados ainda podem ter nomes dados7, mas a versão do
executável e os fontes ensaiados são dados.8; não são resultados antigos.

Permanecem os gates da versão maior: ABI/bytecode definitivos, migração de uma
réplica operacional completa, soak prolongado, UI nativa e plataformas ainda
não homologadas. Esta revisão não transforma o candidato em versão estável.
