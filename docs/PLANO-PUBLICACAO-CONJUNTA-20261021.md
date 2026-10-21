# Publicação conjunta — trabalho em andamento

## Revisão textual r2 publicada e conferida — 21/10/2026

- Após confirmação do usuário, manual público e espelho conferidos com
  SHA-256 `020fa13b9625aa1eb40ddae1b0fcf2f1ea63df0647c82cc16c757cc582a5e881`.
  HTTPS normal, `index.html` e URL com revisão retornaram 200 e os mesmos bytes.
- A seção `depure-analise` agora diz "Disponível desde a Santafé 2.1.0.".
  Varredura do texto público sem avisos incorretos de candidato, preparação,
  desenvolvimento ou versão ainda não publicada. O único trecho semelhante
  a "não ... publicada" trata legitimamente do sigilo da senha no PULSO.
- Ajuda instalada preservada no hash r1 e conferida: Bibliotecas1.0.0,
  distribuição2.1.0 e catálogo oficial disponível. Nenhuma regressão textual.
- Validação do manual instalado passou novamente: 1.240 IDs, 582 funções,
  171 exemplos, 260 contratos C e 344 Fé. Conferência somente em leitura no
  servidor; nenhum serviço ou arquivo operacional foi alterado.
- Pendência textual do manual público encerrada. Downloads/snapshots
  históricos permanecem imutáveis conforme escopo da atualização.

## Revisão textual r2 pronta — 21/10/2026

Pedido: corrigir a última frase de `depure.analise`, validar e enviar.
Agora diz "Disponível desde a Santafé 2.1.0.". Comparação byte a byte com
o manual r1 confirmou que apenas essa frase foi substituída. Fonte local
atualizada; nenhum pacote imutável reescrito.

- Publicador adaptado para dois destinos apenas: manual público e espelho
  `site-sfdev/manual.html`. A ajuda do CLI acompanha só como referência para
  testes; não é destino desta revisão. Mantém backup, rollback, proteção contra
  deriva/symlinks e conferência HTTPS. Não reinicia serviços.
- Dez testes locais passaram, incluindo prova de alteração de uma única frase
  e garantia de que o plano padrão não toca o CLI. Manual validado localmente
  e no Debian: 1.240 IDs, 582 funções, 171 exemplos, 260 contratos C e 344 Fé.
- Entrega em `dist/textos-2.1.0-r2`, enviada para
  `/tmp/santafe-textos-2.1.0-r2.RF1jf9tv`; todos os SHA-256 conferidos.
  Pré-validação remota terminou com `TEXTOS_2_1_0_R2_PREFLIGHT_OK`, código zero,
  incluindo ajuda dos três comandos e suíte do gerenciador em prefixo isolado.
- Manual novo: `020fa13b9625aa1eb40ddae1b0fcf2f1ea63df0647c82cc16c757cc582a5e881`.
  Lançador: `9b4b2fe077de4b2b6523a1a2f59b815bbe5be2a219a48bf75a018aa231b6cdca`.
- Após o ensaio, os hashes de produção continuavam os de r1; portal, dois
  Carteiros e IMAP ativos. Nenhum sudo, instalação ou publicação realizado.

Próxima ação do usuário:

```bash
sudo bash /tmp/santafe-textos-2.1.0-r2.RF1jf9tv/publicar-textos-santafe-2.1.0-r2.sh
```

Depois conferir o manual público e seu novo hash; não declarar publicado antes.

## Conferência da revisão textual publicada — 21/10/2026

- Publicação `2.1.0-textos-r1` confirmada: manual público e espelho têm
  SHA-256 `42f164c505026a16198bfaebc7389a6bd71b24dafb2030b8cfa5309d86078a04`;
  CLI instalado tem `a1b522fdc3c292702666ef7663358d6d554d260b24399306923e1e1fa0ce5ac9`.
- HTTPS nas URLs `/manual/`, `/manual/index.html` e URL com revisão devolveu
  exatamente o manual novo. A ajuda real de `instale`, `empacote` e `catalogo`
  informa Bibliotecas1.0.0, Santafé2.1.0 e o catálogo disponível, sem aviso antigo.
- Manual instalado validado novamente: 1.240 IDs, 582 funções, 171 exemplos,
  260 contratos C e 344 Fé. Portal, dois Carteiros e IMAP permanecem ativos
  com os mesmos horários de início; não houve reinício nesta conferência.
- Busca ampla no texto público encontrou zero ocorrências de candidato ou
  pré-publicação. A ocorrência de "não ... publicada" é a regra legítima
  de sigilo da senha no PULSO, não um estado de versão.
- **Ainda restou uma frase desatualizada**, não contemplada na revisão r1:
  `depure.analise` (âncora `depure-analise`, fonte linha 5882) diz
  "API nova, ainda em desenvolvimento." A API já integra o núcleo 2.1.0
  publicado. Informar essa pendência; a conferência não autoriza publicar
  outra correção automaticamente. Nenhum arquivo de produção foi alterado.

## Revisão textual pronta para publicação — 21/10/2026

Pedido posterior: corrigir manual/ajuda, validar e enviar a atualização.
Corrigidas seis linhas textuais do manual (gabaritos, versões dos editores,
SLS, bibliotecas e `depure.lexemas`) e somente o bloco de ajuda do CLI.
Os exemplos/IDs e a lógica do gerenciador permanecem idênticos.

- Fontes locais: `docs/manual.html` e `ferramentas/pacotes/cli.fé`.
  Publicador/empacotador em `operação/*textos-2.1.0.py`; testes em
  `testes/integracao/testar_textos_2_1.py`.
- Oito testes passaram: textos antigos, alteração de lógica, deriva de alvo,
  symlink, concorrência, idempotência, restauração e falha parcial.
  No macOS o fixture foi ajustado para o caminho temporário resolvido
  (`/private/var`, não o symlink `/var`); proteção do publicador preservada.
- Validação local e Debian: manual com 1.240 IDs, 582 funções, 171 exemplos,
  260 contratos C e 344 Fé; ajuda dos três comandos, compilação do CLI e
  suíte real do gerenciador passaram. `git diff --check` sem problemas.
- Entrega `dist/textos-2.1.0-r1` enviada para
  `/tmp/santafe-textos-2.1.0-r1.WvcdLhvo`; todos os hashes conferidos.
  Pré-validação remota terminou com `TEXTOS_2_1_0_PREFLIGHT_OK` (código zero),
  usando cópia do núcleo/ferramentas em prefixo temporário. Não houve sudo,
  publicação ou reinício; hashes de produção ainda são os anteriores.
- Apenas três destinos: manual público, espelho `site-sfdev/manual.html` e
  ajuda instalada `ferramentas/pacotes/cli.fé`. Backup reversível, verificações
  pré/pós-troca e HTTPS normal/sem cache; não altera downloads, snapshots,
  catálogos ou versões. A revisão exata é guardada junto do backup.
- Manual novo SHA-256:
  `42f164c505026a16198bfaebc7389a6bd71b24dafb2030b8cfa5309d86078a04`.
  CLI novo: `a1b522fdc3c292702666ef7663358d6d554d260b24399306923e1e1fa0ce5ac9`.
  Lançador: `0875680b16c153cee5aa19c23a9badd4c43410474d9e6afb7ed5366c8e945e9d`.

Próxima ação do usuário:

```bash
sudo bash /tmp/santafe-textos-2.1.0-r1.WvcdLhvo/publicar-textos-santafe-2.1.0-r1.sh
```

Depois conferir a publicação real. Os TAR/ZIP 2.1.0 imutáveis continuam com
os textos históricos; a fonte local corrigida será incorporada na próxima
distribuição, sem substituir silenciosamente os downloads já publicados.

## Verificação da publicação real — 21/10/2026

Após o usuário informar que publicou, verificações em leitura e testes isolados
confirmaram a instalação. Este adendo local não modifica o TAR imutável nem
publica qualquer correção.

- `/usr/local/bin/santafé` e `santafec`: 2.1.0; teste da instalação passou
  (bibliotecas operacionais, PDF e handshake real do SLS 1.0.0).
- Os 707 destinos correspondem aos hashes do plano final de
  `/tmp/santafe-conjunto.jdQWgBab/preparado/plan.json`.
- SLS instalado: bateria 1.0 com 39 OK, zero falhas/pendências funcionais.
  A mensagem genérica sobre gates externos da bateria não substitui a
  homologação já registrada nem o registro real de publicação conferido.
- Gabaritos no núcleo/compilador publicados: 1.320 nomes, NFC/NFD, dois
  curingas, fonte/bytecode e UTF-8 inválido passaram.
- Bibliotecas 1.0.0: suíte CLI passou; em projeto temporário foi instalado
  `semver 1.0.0` pelo HTTPS público, importado e testado, reinstalado com
  `--travado` e `--sem-rede`, preservando o lock. Temporário removido.
- HTTPS direto (não cache de busca): 17 arquivos públicos têm os hashes
  esperados, incluindo TAR, ZIP, VSIX 1.1.0, Sublime 1.1.0, manual, WASM,
  catálogo v1, pacote semver e manifestos. `/baixar` anuncia 2.1.0/SLS1.0.0/
  Bibliotecas1.0.0. Catálogo Sublime próprio oferece 1.1.0; isso não confirma
  atualização no Marketplace nem no canal externo Package Control.
- Manual estrutural/sintático passou: 1.240 IDs, 582 funções colapsáveis,
  171 exemplos executáveis, 260 contratos C e 344 contratos Fé.
- Portal e dois Carteiros/IMAP ativos; portal iniciado em 21/10 às 07:33:16
  -03. Carteiros/IMAP conservam inícios anteriores à publicação. Nenhum
  serviço foi reiniciado durante esta auditoria.
- **Pendência documental confirmada também por HTTPS:** o manual ainda
  descreve gabaritos Unicode, SLS, gerenciador/catálogo e `depure.lexemas`
  como não publicados, citando 2.0.3 como estável. A ajuda instalada de
  `santafé instale --ajuda` também diz que o repositório não foi publicado.
  As notas no TAR registram o estado anterior à publicação. São textos
  desatualizados, não falha de instalação; não os corrigir em produção sem
  pedido de alteração e não reescrever os artefatos imutáveis 2.1.0.

Próxima ação: informar o sucesso operacional e a pendência textual; preparar
revisão documental somente quando solicitada. Não houve push/etiqueta ou
publicação externa nesta verificação. Automação permanece pausada.

## Concluído — entrega final conferida em 21/10/2026

Adendo posterior ao TAR; não altera os bytes já pré-validados.

- Pacote final em `/tmp/santafe-entrega-2.1.0-final.K8btVOEQ`, servidor
  `servidorsfdev`. TAR SHA-256:
  `2075f756a689eaf54952909d6b551a82a5df127c23897ac6bf3c04d1fe3e2d64`.
- Pré-validação exata terminou com código zero/`CONJUNTO_PREFLIGHT_OK` em
  `/tmp/santafe-conjunto.jdQWgBab`: compilação, regressão, instalação isolada,
  39/39 SLS fonte e instalado, bibliotecas/TLS, WASM, manual e 707 destinos.
  Relatório final: `dist/conjunto-2.1.0-final/RESULTADO.json`; logs em `evidencias/`.
- Hosts e pixels dos dois editores aprovados. Sublime1.1.0 instalado e conferido;
  VS Code1.1.0 testado em perfil temporário, sem substituir a extensão global.
  Plugin temporário Sublime guardado em backup recuperável; documentos intactos.
- Verificador final (sem `--preflight`) passou no servidor. Núcleo de produção
  ainda 2.0.3; portal, dois Carteiros e IMAP ativos. Nada instalado/reiniciado.
- Automação `preparar-santaf-sls-e-bibliotecas-1-0` PAUSADA após conclusão.
  Próxima ação é do usuário: executar o comando abaixo. Depois conferir a
  publicação real; GitHub/Marketplace/canal externo não foram alterados.

```bash
sudo bash /tmp/santafe-entrega-2.1.0-final.K8btVOEQ/publicar-santafe-conjunto-2.1.0.sh
```

## Retomada após liberação do aviso — 21/10, manhã

- Usuário fechou o aviso; host Sublime 4215/Santafe1.1.0/SLS1.0.0 passou.
  Suítes nativas: 175 realce, 43 concatenações, 612 API/paletas, zero falhas.
- VS Code repetiu o host real; captura final com SLS1.0.0/extensão1.1.0 e
  54 conclusões. Pixels de ambos inspecionados, paleta suave/gabaritos/HTML/JS
  corretos. Anotação JS do fixture corrigida para `--[[javascript]]`, conforme
  contrato existente; não foi adicionada sintaxe nova.
- Provas consolidadas em `docs/HOMOLOGACAO-CONJUNTA.json` e logs/capturas em
  `docs/evidencias/conjunto-20261021`; gates técnicos fechados no manifesto.
  Documentação atualizada; somente a ajuda do CLI deixou de dizer candidato.
- Próximo: empacotar entrega final, conferir diferença contra ensaio4, repetir
  pré-validação dos bytes finais no Debian, enviar comando confirmado. Sem
  produção/GitHub/Marketplace. Pausar a automação somente ao concluir.

## Handoff técnico — conjunto final de ensaio 4 concluído

Este adendo é posterior ao TAR; não altera os bytes do artefato já ensaiado.

- **Ensaio 4 passou integralmente**, com os fallbacks NFC/NFD corrigidos.
  Entrega no servidor: `/tmp/santafe-entrega-2.1.0.IwUPClzJ`.
  Compilação/instalação isoladas: `/tmp/santafe-conjunto.JW2rLJ78`.
  TAR SHA `1523a4cfa332ad6a314f8a8978e9b339eab1afac4f6d8c94289ad7c596a61b2e`.
- Relatório e logs locais: `dist/conjunto-2.1.0-ensaio4/RESULTADO.json` e
  `evidencias/`. TAR/ZIP/lançador enviados e hashes conferidos. Extensões
  compiladas no Mac/Debian têm bytes idênticos; WASM também foi reproduzido.
- Núcleo de produção continua 2.0.3; portal, dois Carteiros e IMAP ativos.
  Nenhum sudo, instalação, reinício, GitHub ou Marketplace realizado.
- Implementação/testes independentes concluídos. **Não repetir todas as
  baterias sem mudança de fonte.** Falta o host/visual Sublime e a inspeção
  visual VS Code. Não há `HOMOLOGACAO-CONJUNTA.json`; o publicador continua
  bloqueado por projeto. Não enfraquecer o bloqueio para declarar sucesso.
- Ao retomar, conferir se a janela modal Sublime foi resolvida. Se não houve
  mudança, permanecer quieto; não insistir com comandos enfileirados, não
  clicar às cegas nem reiniciar o aplicativo. Com acesso visual restabelecido,
  usar somente os projetos/perfis temporários descritos abaixo, concluir os
  ensaios e registrar a homologação. Só então preparar o pacote publicável.

### Verificação de continuidade — 21/10, 06h26 BRT

- Relatórios Sublime sem alteração: erro de 04h02 e recursos de 04h06;
  relatório de host concluído ainda ausente.
- Consulta de processos e amostra de pilha somente em leitura confirmaram
  o mesmo PID 31489 aguardando `NSAlert runModal`/`runModalForWindow:`.
  Nenhum comando novo foi enfileirado no editor; nenhum diálogo foi fechado.
- Sem mudança nos fontes ou artefatos. Próxima ação permanece a resolução
  visível desse diálogo para então executar os testes pendentes.

## Estado corrente — 21/10, 05h20 (prevalece sobre históricos)

- Publicador/lançador conjuntos agora implementados e ensaiados. Debian dos
  conjuntos 2 e 3 concluiu compilação, regressão, instalação isolada, 39/39 SLS
  no fonte e no prefixo, bibliotecas, WASM, catálogo, manual e plano reversível.
  Ensaio 3: `/tmp/santafe-entrega-2.1.0.C3DZxGxP/preflight.log`, árvore
  `/tmp/santafe-conjunto.98wbuF8L`. Nenhuma instalação/serviço alterado.
  TAR SHA-256: `75da11d85cf7b77afb32de42d6841adb6f472d5a19b0d39fc14f3f054912e687`.
- Corrigida a URL oficial com `est%C3%A1tico`: o padrão anterior não aceitava
  percentuais. TLS real agora testa esse caminho e rejeita escapes inválidos,
  travessia codificada, controles e downgrade. Passou macOS e Debian (ensaio 3).
- CI não depende mais de VSIX histórico em dist ignorado: fixtures antigas
  explícitas, pacotes atuais reais e versão da distribuição lida do manifesto.
- VS Code **host real** repetido com extensão1.1.0/SLS1.0.0 e `-E -P`: passou;
  `/tmp/santafe-vscode-host-sls-final-20261021.json`. Sem inspeção de pixels.
  TextMate real: 175 casos e cores Dark+/Monokai. Sublime: mock, pacote, 43
  concatenações e 3.000 fragmentos passaram; host/visual continua bloqueado.
- Depois do ensaio 3, corrigidos e testados dois fallbacks sem SLS: nomes NFD
  nas conclusões locais Sublime e na navegação local VS Code. Pacotes novamente
  gerados; repetir o conjunto final após estes ajustes. Não atribuir os hashes
  anteriores aos bytes novos.
- O pacote Sublime candidato foi atualizado em disco; backups em
  `/tmp/santafe-editores-backup-zIUqtW`. A configuração do projeto temporário
  usa `-E -P`. Não encerrar aplicativo/documentos nem clicar na janela modal
  sem conseguir inspecioná-la. Instalação global VS Code não foi substituída.
- Próximo: relatório/artefatos finais, último preflight exato, upload conferido.
  Manter publicação bloqueada até fechar o host/visual Sublime e a inspeção
  visual VS Code. Não há prova final de homologação, GitHub/Marketplace não
  foram alterados. Não dizer que SLS 1.0 está publicado ou homologado em ambos.

### Estado anterior — após ensaio Debian 5

- Debian.5 concluído integralmente, incluindo bibliotecas/instalação/WASM:
  `/tmp/santafe-auditoria-sls.MQMgKtfi/santafe-2.0.4-auditoria.5`.
  SHA do TAR `7c4330631b84f0188683c1dc1bc6cc29f7ee58766a6d3529b1933d4566716713`.
  Logs locais `/tmp/santafe-debian-bibliotecas-20261021`. Sem produção alterada.
- Após isso: catálogo real/gerador de curadoria, testes de imutabilidade e
  upgrade interrompido, planner transacional/publicador, docs, correção de
  warnings C e inicialização SLS `-E -P`. Repetir Debian com conjunto final.
- Fonte identifica candidatos núcleo2.1.0/SLS1.0.0/gerenciador1.0.0/ext1.1.0.
  Não são versões publicadas. `operação/conjunto-versoes.json` guarda gates
  abertos, `verificar-conjunto.py` recusa publicar sem prova final. Nenhuma
  prova de homologação foi fabricada. 39/39 +24incrementais passaram de novo.
- `operação/preparar-conjunto.py`, `publicar-conjunto.sh`, curadoria e testes
  existem. Falta lançador com hashes, pacote final, preflight integrado real,
  atualização dos documentos de evidência e upload conferido.
- Sublime bloqueado por **NSAlert runModal** (sample read-only), não diagnóstico
  de bug no pacote. Sem texto/pixels acessíveis. Não fechar/pressionar nada às
  cegas. Testes nativos/visuais pendentes. CLI sessões antigas podem continuar
  aguardando; não matar o editor. Tempplugin SantafeHomologacao deve ser limpo
  somente ao terminar; preservar backup original1.0.13.
- VS Code: repetir host isolado após `-E -P` e versão1.0.0; perfil temporário
  `/tmp/santafe-profile-sls-rro191` já atualizado. Ainda sem captura visual.
- Próximo: gerar catálogos/extensões, testes, lançador, preflight Debian e
  artefatos prontos; não alegar liberação final enquanto gates visuais faltam.

Pedido de 21/10/2026: corrigir gabaritos Unicode, concluir o contrato SLS 1.0
e depois implementar o gerenciador/repositório oficial de bibliotecas 1.0.
Não publicar produção, Marketplace, catálogos externos, etiquetas ou GitHub
antes da validação final do usuário. É autorizado enviar artefatos conferidos
a `/tmp` do `servidorsfdev` e executar testes isolados sem instalar/reiniciar.

## Continuidade

Automação deste chat: `preparar-santaf-sls-e-bibliotecas-1-0`, a cada 20 minutos.
Retomar pelo estado real dos arquivos/testes, sem repetir tarefas concluídas.
Pausar a automação ao concluir ou se o usuário cancelar. Não criar novas
automações duplicadas. Não delegar a outros agentes sem autorização específica.

## Estado inicial comprovado (histórico, superado pelo estado corrente)

- Gabaritos `®variável` e `Ⓡvariável`: núcleo e gramáticas/recortadores dos
  editores corrigidos para letras Unicode, marcas combinantes e números após
  o primeiro caractere; NFC e NFD aceitos sem normalizar a identidade.
- Corrigida também corrupção de pilha no crescimento de `luaL_Buffer` durante
  interpolação. Testes de estresse, 1.320 nomes, bytecode, ASan/UBSan,
  regressão geral e testes automatizados de realce aprovados localmente.
  Evidências: `AUDITORIA-GABARITOS-UNICODE-20261021.md`.
- SLS: primeira etapa existente `0.2.0-dev.1`, intervalos reais do compilador,
  sincronização incremental UTF-16 atômica e limites; alvo 1.0 ainda incompleto.
  Contrato obrigatório: `SLS-1.0.md`. Último alvo: 15 OK, 24 pendentes, zero
  falhas; isso NÃO homologa 1.0.
- Produção consultada somente em leitura: núcleo 2.0.3, SLS publicado 0.1.1.
- Editores instalados consultados: VS Code 1.0.7 e Sublime 1.0.13.
  As correções atuais ainda não foram instaladas nem testadas visualmente.
- Não houve upload/publicação desta entrega, alteração de versões ou push.
- Preservar todas as alterações existentes da árvore `desenvolvimento`.

## Sequência e critérios

1. Expor tokens com intervalos usando o lexer REAL, sem executar fonte;
   recuperação lexical limitada, memória/GC seguros e testes adversariais.
2. Análise estrutural, escopos, vínculos, importações estáticas seguras e
   catálogo comum; navegação, conclusões, ajuda, rename conservador.
3. Formatação/seleção/dobramento/tokens/correções, cancelamento e limites.
   Passar a bateria-alvo e ampliar adversariais, não reduzir os critérios.
4. Integração e atualização dos dois editores; testes nos hosts reais e
   inspeção visual quando disponível. Registrar claramente o que não pôde
   ser observado. Instalação macOS/Linux, WASM, regressão e benchmarks.
5. Gerenciador/repositório de bibliotecas: contrato e implementação 1.0 com
   instalação por projeto, resolução, lockfile, integridade, builds nativos
   controlados, transações, segurança e testes sem dependência de produção.
6. Documentação/versões coerentes, artefatos imutáveis e publicador reversível.
   Upload verificado e preflight Debian/WASM isolado; entregar o comando real.

## Próxima ação

### Atualização da etapa semântica (21/10, em andamento)

- Implementada `depure.lexemas` protegida, baseada no lexer do compilador;
  fonte até 16 MiB, tokens limitados, GC e buffer liberado após erros.
- Novos módulos Fé `analisador`, `projetos`, `semantica` e suporte privado
  POSIX `nativo.c` (leitura confinada por openat/O_NOFOLLOW, arquivos regulares).
  Build/instalador/desinstalador já incluem esses componentes.
- SLS fonte agora **0.3.0-dev.1**, não publicado. Escopos/Pratt parser,
  referências Unicode/gabaritos, imports sem execução, conclusões/catálogo
  comum, hover, assinatura, navegação, rename versionado, símbolos, tokens,
  formatação conservadora, dobramento/seleção e quickfix de fim ausente.
- Bateria-alvo: **39 OK / 0 falhas / 0 pendentes** em
  `/tmp/sls-contrato-1.0-em-progresso.json`. NÃO equivale a 1.0 homologada.
- 13 adversariais passaram (inclui corpus real válido, colisões/captura de
  nomes, NFC/NFD, symlinks, aliases reatribuídos, preservação de literais).
  As três falhas inicialmente encontradas foram corrigidas e retestadas.
- Incremental: 24 testes OK. Teste original LSP OK. Testes Fé novos de lexer
  e analisador OK. Ainda repetir regressão completa, sanitizadores e Linux.

Próximas pendências críticas antes dos editores: múltiplos diagnósticos,
cancelamento real, índice de todos os arquivos dentro dos limites (hoje só
abertos/importados), segurança de rename de campos/aliases dinâmicos, testes
de escala e memória, raiz/indexação segura. O parser incremental ainda não
existe: transporte incremental e análise integral. Não alegar o contrário.
Depois: integrar provedores dos clientes sem duplicação, instalar/validar
ambos, testes visuais, Linux/WASM, gerenciador de bibliotecas e publicação.

Continuar em Fé, sem dependência Python nova para o usuário. Não reduzir gates.

Atualizar este registro a cada etapa com comandos, resultados e pendências.

## Estado mais recente — 21/10, madrugada (substitui os estados acima)

### Núcleo/SLS/editores

- Núcleo: Unicode NFC/NFD, marcadores ®/Ⓡ e interpolação grande corrigidos.
  Lexer real com filhos de gabaritos, limites e preservação de `LUA_ERRMEM`.
- SLS fonte **0.3.0-dev.1**, não rotulado 1.0: 39/39 critérios funcionais,
  23 adversariais semânticos, 24 incrementais, 5 de cancelamento. Índice
  confinado, múltiplos diagnósticos, rename conservador, aliases/campos,
  watchers/raízes dinâmicas, limites de CPU, quadro e memória implementados.
- Memória: 900 falhas de alocação + 3.000 entradas arbitrárias, sem vazamento
  do alocador/descritores; ASan/UBSan e API checks passaram. Mac retém páginas
  do alocador no ensaio prolongado; Debian estabilizou em ~104 MiB.
- Regressão geral, manual, prefixo com espaços e instalação macOS passaram.
  MariaDB/DNS que exigem configuração seguem explicitamente SKIP.
- Debian isolado **concluído com sucesso**, instalação e WebAssembly inclusive:
  `/tmp/santafe-auditoria-sls.tjaTXE/santafe-2.0.4-auditoria.3` no servidor.
  Relatórios recuperados em `/tmp/santafe-debian-auditoria-20261021` no Mac.
  Arquivo enviado: `santafe-2.0.4-auditoria.3.tar.gz`, SHA-256
  `fc3037ead34888a751f1e2b0786dbbb55afcfec2fc482370c438a51403059aea`.
  Este arquivo precede a implementação do gerenciador; NÃO é publicação.
- Extensões candidatas **1.1.0**: provedores semânticos, watchers, incrementais,
  snippet de função corrigido (sem bloco início redundante). TextMate 175 casos,
  40 concatenações e 3.000 fragmentos, paletas, mock e nove snippets passaram.
- Host real VS Code passou: `/tmp/santafe-vscode-host-sls-1.1.0.json`.
  Perfil isolado, sem documentos do usuário. A instalação global ainda não foi
  trocada. Não houve inspeção de pixels da versão nova.
- Sublime: pacote candidato instalado em disco, backup original1.0.13 em
  `/tmp/santafe-editores-backup-zIUqtW/Santafe-anterior.sublime-package`.
  O processo antigo não recarregou o recurso `Packages/Santafe/Santafe.py`;
  `load_resource` dá FileNotFoundError embora `find_resources` liste o arquivo.
  CLI de comando ficou sem resposta. Não encerrar editor nem perder documentos.
  Captura de tela falhou: `could not create image from display`; sem evidência
  visual. Testes reais Sublime permanecem pendentes, não aprovados por inferência.
  Plugin temporário de testes `Packages/SantafeHomologacao` deve ser retirado
  ao concluir; preservar qualquer plugin de auditoria anterior do usuário.

### Bibliotecas — implementação iniciada, ainda não 1.0

Contrato: `REPOSITORIO-BIBLIOTECAS-1.0.md`. Módulos em `ferramentas/pacotes`:
`versoes`, `resolvedor`, `formatos`, `cliente`, `administracao`, `ambiente`,
`cli`, suporte privado POSIX/GLib `nativo.c` e Makefile.

- SemVer/backtracking determinístico: 87 critérios OK; travas, diamantes,
  prévias explícitas, limites, conflitos e ciclos. Uma versão por pacote.
- Envelope `.sfp` JSON fechado, Base64 estrito, SHA-256, arquivos explícitos,
  licença/README/autoria/fontes; caminhos sem links/travessia/especiais e
  colisões de caixa/NFC. Catálogo local imutável por nome/versão.
- Instalação por projeto, cache, offline, gerações, trava flock, journal e
  recuperação; manifesto/lock são espelhos, estado atômico aponta para geração.
  Falhas antes do commit preservam anterior; depois finalizam; edição manual
  detectada não é sobrescrita. Gerações antigas são mantidas, sem limpeza ampla.
- Bibliotecas C exigem `--permitir-nativo`; receitas de fontes/nomes de libs,
  sem shell/hooks, compilador local com ambiente mínimo, limites e timeout.
  Isso NÃO é sandbox contra código nativo. Nenhum sudo automático.
- CLI nativo `santafé instale/empacote/catalogo`, bootstrap de dependências no
  diretório atual, `-P` para desativar. Ferramentas encontradas ao lado do
  executável, nunca pelo cwd/PATH. Carregador lê/hash-confere fonte antes de
  executar via importe. SLS lê a geração sem executar, rename recusa bibliotecas.
- Ensaios iniciais de integração macOS passaram: determinismo, imutabilidade,
  instalação, offline, seis fases de interrupção, symlink/FIFO/trava, compilação
  C recusada/permitida, execução real e subprocesso sem shell/credenciais.
  Bateria está sendo ampliada para SLS, primeira instalação interrompida,
  conflito de edição manual, origem offline, CLI/prefixos e casos adversariais.
- Limites: 128 pacotes, 256 versões/pacote, 20.000 passos, 8.192 arquivos/
  128 MiB instalados e 32 módulos C. Pacote até 512 arquivos, 32 MiB de dados.
- Nada no catálogo oficial foi publicado. Nenhuma versão/etiqueta foi registrada.

### Próximas ações concretas

1. Concluir/testar gerenciador: CLI/prefixos, conflitos/rollback com versões
   realmente diferentes, TLS/redirecionamento/download, falhas de alocação e
   revisão C, limites, integração SLS e regressão completa. Verificar Windows
   explicitamente fora do suporte POSIX inicial; não anunciar funcionamento.
2. Repetir Debian/WASM após alterações ao CLI/gerenciador e SLS recentes.
   Upload somente artefatos conferidos, execução isolada; não instalar sistema.
3. Resolver/registrar limitação real do Sublime sem fechar documentos; não
   confundir teste de gramática/mock com host/visual. Reempacotar extensão após
   watcher de `.santafe/estado.json` (cópia em disco está anterior a isso).
4. Atualizar manual/API lexer, auditorias, README extensões, README gerenciador,
   catálogo/página de bibliotecas, versões, CI e pacote de distribuição somente
   depois dos gates. Publicador reversível/artefatos+hashes, envio a `/tmp` e
   comando conferido para o usuário. NÃO dar comando de um arquivo inexistente.
