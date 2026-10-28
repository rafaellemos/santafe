# Publicação conjunta — trabalho em andamento

## Editores 1.1.1 — portal preparado, ainda não publicado — 21/10/2026

- Retomada solicitada pelo usuário antes da auditoria de linguagens. Essa
  auditoria/migração não foi iniciada; a entrega abaixo atualiza exclusivamente
  os arquivos dos editores e a página de download, não uma nova versão do núcleo.
- Marketplace 1.1.1 já público e submissão Sublime #9622 atualizada, ainda
  aberta/não integrada. CI do commit `802df7d` passou nos dois workflows:
  execuções `39599366034` (SLS/bibliotecas) e `39599366025` (núcleo/manual/editores).
- Portal `/baixar` e catálogo HTTPS próprio ainda oferecem 1.1.0. Preparada
  atualização independente para 1.1.1, com READMEs corrigidos, link do
  Marketplace e indicação explícita da aprovação pendente do catálogo geral.
  O catálogo próprio declara Sublime >=4171, como a submissão oficial, e inclui
  SHA-256 do pacote. Os arquivos versionados anteriores permanecem intocados.
- Publicador e empacotador: `operação/*editores-1.1.1.py`. Reutilizam a transação
  existente, mantêm backup/rollback, recusam deriva, links simbólicos e
  substituição de artefatos imutáveis. Plano limitado a 12 arquivos: página e
  espelho, VSIX, Sublime manual/versionado, catálogo e somas. Núcleo, SLS, manual,
  gerenciador, fontes históricas e aplicações empresariais não são destinos.
- 11 regressões passaram localmente, além das suítes de ambos os editores e do
  publicador histórico. Novo teste adicionado ao workflow, ainda não enviado ao
  GitHub nesta etapa; não confundir com os runs verdes anteriores.
- Entrega local: `/private/tmp/santafe-portal-editores-1.1.1.tt35eMZp/entrega`.
  Enviada para `/tmp/santafe-editores-1.1.1.dQuL6uOz/entrega` no servidorsfdev.
  Todas as somas conferidas; pré-validação real com `santafec -p`, integridade
  dos pacotes/READMEs, plano e estado do portal terminou com
  `EDITORES_1_1_1_PREFLIGHT_OK`, código zero, sem sudo.
- Após o pré-teste, hashes do portal, núcleo, lançador SLS, manual e TAR/ZIP
  2.1.0 continuaram idênticos aos anteriores; horários dos quatro serviços
  conferidos também permaneceram iguais. Nenhuma instalação ou reinício.

Próxima ação do usuário:

```bash
sudo bash /tmp/santafe-editores-1.1.1.dQuL6uOz/entrega/publicar-editores-1.1.1.sh
```

A publicação reinicia somente `sfdev.service`, verifica arquivos e respostas
HTTPS, e restaura a versão anterior em caso de falha. Depois conferir o portal
e o catálogo próprio; não declarar publicado antes da execução do usuário.

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

## Rodada posterior — candidato de dados.3, 23/10/2026

O registro acima descreve o trabalho histórico de 21/10, não o estado atual
da versão estável. A rodada atual é o experimento de nova semântica de dados,
sem instalação em produção. Retomar por `experimentos/dados-v3/PLANO.md` e
`experimentos/dados-v3/RELATORIO.md`.

Bibliotecas migradas em árvore isolada: macOS/Debian, 76 ensaios gerais + 12
em banco temporário próprio; SLS 39 adversariais + 39 LSP em cada plataforma;
WASM 15 casos e recuperação; núcleo/ONFÉ, ABI e sanitizadores conforme relatório.
Nada foi publicado, etiquetado ou enviado ao Git. Restam a cadeia integral de
aplicativos/ferramentas, UI, compatibilidade final e os gates da versão maior.

## Continuação — candidato dados.4, 23/10/2026

Retomar por `experimentos/dados-v4/PLANO.md` e `RELATORIO.md`. O usuário pediu
seguir a bateria sem refazer a demonstração. Corrigida a migração do gerenciador
(listas, nulos, serialização canônica, retrocesso do resolvedor e ABI nativa).
Dez baterias adicionais passaram em macOS/Debian; regressões de bibliotecas,
12 ensaios SQL em instância temporária, 39 SLS e 39 LSP em cada sistema;
WASM 16 casos e recuperação. Um ensaio adicional expôs controles crus e
truncamento no NUL aceitos pelo decodificador JSON: corrigidos no modo
experimental e todas as baterias repetidas após a correção.
ASan/UBSan passou nos harnesses nativos e de lexer no Mac. Produção intacta.
Faltam aplicativos integrais, distribuição/rollback, plataformas e inspeção
visual atual; nenhuma aprovação estável foi inferida dessa bateria.

## Continuação — dados.5 e dados.6, 23/10/2026

Retomar por `experimentos/dados-v6/RELATORIO.md` e `PLANO.md`.
Dados.5 fechou 13 percursos reais dos aplicativos, instalação, oito pontos de
rollback e atualização entre candidatos. Dados.6 acrescentou gerações isoladas
com trava/journal/troca atômica (300 leituras, 20 trocas, sete grupos), carga
concorrente com proteções ativas em macOS/Debian, 200 edições incrementais SLS,
manual candidato (174 exemplos compilados, 12 executados), WASM 16 casos e
três demonstrações reais no navegador. Corrigidos fila IMAP vazia, descrições
de nulo/listas/JSON/SQL, caminho WASM antigo e transbordamento móvel do manual.

Regressão de editores: 25 TextMate/embutidos e 17 recorte Sublime; UI nativa
indisponível nesta sessão, não aprovada. Manual visual em 390/1280 px tem
capturas; fonte de ícones da prévia ainda apresenta fallback. A migração
operacional ensaiada não equivale a troca completa dos serviços estáveis.
Fontes/evidências/checksums em `dist/candidato-dados-v6`; servidor somente /tmp.
Nenhuma instalação/publicação/reinicialização em produção, tag ou push.
Gates restantes enumerados no relatório: ABI/bytecode, ONFÉ atômico, migração
completa de dados/configurações, soak prolongado, UI nativa e plataformas.
# Continuação — dados.7, 23/10/2026

Retomar por `experimentos/dados-v7/RELATORIO.md` e `PERSISTENCIA.md`.
Usuário decidiu manter listas sem metatabelas nesta versão. Implementadas
gravações ONFÉ síncrona/assíncrona com substituição atômica, estados explícitos
inalterado/publicado/durável, descritor do diretório fixado e teste de falhas.
ONFÉ instalado em bibf; completude SLS, manual e manifesto de APIs atualizados
apenas na árvore candidata. macOS Intel/Debian: 17 grupos ONFÉ, sanitizadores
do helper C, núcleo, SLS, instalação/rollback, sete grupos operacionais e 13
percursos dos aplicativos passaram. WASM: 17 casos e recuperação passaram.
Manual: 174 exemplos compilados, 264 contratos C, 351 Fé; 12 exemplos executados.
Base imutável dados.6 preservada. Artefatos finais em dist/candidato-dados-v7.
Servidor usado apenas em /tmp/santafe-dados7.1S7FpWIE. Produção intocada.

Próxima etapa: fechar ABI/bytecode e preparar réplica operacional integral da
instalação estável em laboratório, com migração/retorno de dados; depois soak
prolongado e validação visual/plataformas. Não confundir o ensaio atual de
gerações com uma migração completa da instalação estável. Não publicar nem
reiniciar serviços sem validação final do usuário.

## Continuação — dados.8, 23/10/2026

Usuário decidiu conservar função ... fim e substituir os dois acentos graves
dos colares brutos por [=[...]=], [==[...]==] e níveis superiores com =.
Retomar por experimentos/dados-v8/RELATORIO.md e LEIA-ME.md. A semântica de
quebras é compatível com os colares longos estáveis: uma quebra inicial é
suprimida. Migração lexical a partir de dados.7 preserva o valor acrescentando
uma quebra de proteção quando necessário. [[...]] continua lista aninhada;
um acento grave continua gabarito. ONFÉ não executa gabaritos nem código.

Núcleo, ONFÉ, SLS, kits isolados 0.0.8 dos editores, HTML/JS concatenados,
Prism/manual e migradores atualizados. macOS/Debian: 14 grupos novos,
183 fontes Fé compilados, regressão de 11 etapas, 17 grupos de persistência,
39 testes SLS, recuperação incremental e 13 percursos de aplicativos com
carga de 60s. WASM: 18 casos + recuperação. macOS adicional: aceitação LSP
39/39, 900 falhas de alocação/3.000 entradas, ASan/UBSan do helper atômico.
Kits: 25+45 TextMate/embutidos; 17+7 recorte Sublime; cinco regras Prism.
Manual: 174 compilações, 12 execuções, 264 contratos C e 351 Fé.

Fontes/evidências em dist/candidato-dados-v8; Debian somente em
/tmp/santafe-dados8.fhLMCQzP. Nada instalado em produção ou nos perfis dos
editores; nenhuma tag, push ou publicação externa. UI nativa não foi
homologada nesta rodada. Gates maiores continuam os enumerados em dados.7.

### Dados.8 — hosts dos editores, 23/10/2026

Retomar por `experimentos/dados-v8/VALIDACAO-EDITORES.md`. VS Code 1.142.0:
extensão 0.0.8 e SLS 1.0.0-dados.8 ativos, oito grupos repetidos duas vezes.
Sublime 4215: seis grupos repetidos, escopos/estilos/regiões reais; curingas
laranja normal, paleta suave, HTML/JS concatenados e recuperação de delimitador.
Corrigidos somente os harnesses: Python do Sublime remove assert no modo otimizado;
verificações agora usam exceções explícitas e sentinela. Falhas anteriores do
harness preservadas. TextMate45/Prism5/recorte7 repetidos na árvore candidata;
112 checksums do pacote selado continuam válidos. Produção intocada.

Captura/controle de janelas nativas indisponível: **inspeção de pixels continua
pendente**. Não confundir os ensaios de host com aprovação visual. Laboratório
temporário `santafe-dados8-host-gslwbyhb`; pacote Sublime separado
`SantafeDados8Hostgslwbyhb` ainda disponível apenas para a conferência visual.
Próxima ação: capturas do fixture nas duas janelas; depois arquivar esse pacote
temporário sem alterar Santafe/SantafeDados. Nenhum novo candidato publicado.

### Dados.8 — acesso nativo liberado, 23/10/2026

Após a atualização do aplicativo pelo usuário, leitura e captura das janelas
funcionam nos dois editores. Sublime: inspeção real dos pixels de `visual.fé`
(linhas 1–29) concluída; delimitadores, HTML/JS concatenados, paleta suave,
gabaritos Unicode, listas e comentários sem defeito visual observado.

VS Code: o vínculo nativo selecionava apenas a instância habitual. Aberto o
mesmo kit selado num perfil separado `Santafe dados.8 visual temporario`, sem
substituir extensões do perfil habitual. A janela do candidato agora é visível,
mas inicialmente estava em Modo Restrito. A revisão automática rejeitou
**Confiar**, exigindo confirmação atual. O usuário autorizou somente o workspace
de teste; a confiança foi resolvida e o SLS candidato iniciou corretamente.
Retomar pelo relato em `experimentos/dados-v8/VALIDACAO-EDITORES.md`.
Produção e artefatos selados preservados; nenhum candidato novo gerado.

### Dados.8 — correção após inspeção visual, 24/10/2026

Capturas reais nos dois editores concluídas. Sublime passou sem alteração do
kit. VS Code 1.142.0 expôs falha que os testes de tokens não detectavam: a
propriedade fontStyle na raiz das decorações impedia exibir a paleta suave e
o laranja dos gabaritos. A cópia de laboratório com light.fontStyle/dark.fontStyle
renderiza corretamente e preserva normal/italic. Inserção temporária de função
confirmou ciano oblíquo e atualização ao editar; desfeita após captura.

Correção no fonte compartilhado `extensões/vscode/aparencia.js`; regressão de
API/cores com 612 entradas passou. Patch e hashes para o kit isolado em
`experimentos/dados-v8/correcoes/`. Os 112 checksums selados continuam válidos.
Não confundir a aprovação visual da cópia corrigida com o kit dados.8 original.
A próxima montagem deve incorporar esse patch. Perfis habituais e produção
preservados, sem publicação, reinício de serviços, tag ou push.

Regressão final da cópia corrigida: oito grupos passaram novamente no Extension
Host real, dentro da janela temporária já confiável. Evidência e hashes em
`experimentos/dados-v8/evidencias-host/vscode-correcao-visual*.json`. O comando
temporário de teste foi removido, os fixtures foram restaurados e a janela
recarregada. Tentativa anterior em perfil sem confiança preservada como falha
de preparação do ensaio, não como aprovação. Inspeção visual concluída; próximo
passo de empacotamento é incorporar o patch sem sobrescrever dados.8.

### Dados.9 — preparação, 24/10/2026

Solicitado novo candidato com correção visual, sem produção. Receita em
`experimentos/dados-v9/preparar.py`, base imutável dados.8 SHA-256
`f95592a0737d663f7a70d01a70aa96fda9c83a111c34cdd0d2f8287d5b75cabb`.
Árvore local `/private/tmp/santafe-dados9-fbvcbt5g`; Debian em
`/tmp/santafe-dados9.TVessQnc/arvore`. Fontes enviados somente ao laboratório.
Mantida a decisão de listas adjacentes e colares brutos com pelo menos um `=`.
Correção visual por light/dark.fontStyle incorporada; kits 0.0.9 e SLS
1.0.0-dados.9. Primeira regressão local parou no teste de instalação porque
a expectativa de versão ainda dizia dados.8; logs preservados em
`evidencias/tentativa1-versao-instalada`. Expectativas e identificadores
ajustados, sem relaxar critérios; nova rodada macOS e Debian em andamento.
Próximo: concluir baterias, repetir hosts dos editores, conferir artefatos
e selar a entrega. Não afirmar aprovação antes dos resultados.

### Dados.9 — baterias e visual concluídos, 24/10/2026

Retomar por `experimentos/dados-v9/RELATORIO.md`. macOS e Debian: dez etapas
novas e onze de regressão passaram, 14 grupos de colares, 183 fontes, 17 grupos
ONFÉ atômico, 39 SLS e recuperação incremental, 13 percursos de aplicativos,
carga de 60s, instalação/atualização/rollback e sete grupos de gerações.
WASM recompilado: 18 casos + recuperação. Manual: 174 compilações, 12 execuções,
264 contratos C, 351 Fé. API/cores: 612; TextMate: 25+45; Sublime: 17+7;
Prism: cinco. Logs incluem falhas iniciais e repetições aprovadas.

VS Code 1.142.0: oito grupos no host; Sublime 4215: seis, namespace exclusivo9.
Capturas reais aprovadas em ambos, com kits 0.0.9/SLS 1.0.0-dados.9 e correção
light/dark.fontStyle. Fixtures restaurados; comando temporário retirado e
VS Code recarregado. Perfil temporário mantém nome dados.8, mas versões/hashes
comprovam9. Nenhuma troca de perfil habitual ou produção.

Gerações: Debian observou candidata e estável durante as trocas; macOS só
observou estável. Não ampliar essa evidência. Baseline somente núcleo 2.1,
sem migração de bancos. Gates maiores remanescentes no relatório; não repetir
como pendente a inspeção dos dois editores já concluída.

Próxima ação: conferir que fonte final coincide com os executáveis ensaiados,
selar fontes/kits/WASM/manual/evidências e enviar somente ao diretório de
homologação `/tmp/santafe-dados9.TVessQnc/entrega`. Nenhum comando de produção.

### Dados.9 — entrega confirmada, 24/10/2026

Pacote final: `dist/santafe-candidato-dados.9-homologacao.tar.gz`, SHA-256
`1eaeb9415facdbb0d3f151aaf26e506f667d04b40fb2a7c7288d3d4d2c3836ad`.
Fontes (739): `59cecf0965e3ce5f25a21c667faaea94c689f7fe90bc70632dd6458bb7c3c253`.
Duas montagens dos fontes produziram bytes idênticos. Comparação com o pacote
ensaiado: mudanças posteriores só no plano/receita/delta e adição de relatório,
harnesses de host e selador; código de produto preservado. Dados.8 intacto.

Enviado e extraído em `/tmp/santafe-dados9.TVessQnc/entrega`; 133 checksums
conferidos pelo Python e por sha256sum. 415 fontes de produto/manual comparados
no próprio Debian com a árvore ensaiada: idênticos. Fixtures locais restaurados
e extension.js/package.json/aparencia.js do host temporário iguais ao kit limpo.
O VS Code foi recarregado após retirar a instrumentação. Produção intocada.

Comando de conferência, sem instalar:
`cd /tmp/santafe-dados9.TVessQnc/entrega && sha256sum -c SHA256SUMS`

Esta solicitação de preparar o próximo candidato está concluída. Próxima ação
é a homologação pelo usuário; para a versão maior estável, manter os gates do
RELATORIO.md (ABI/bytecode, réplica completa, soak, aplicativos/plataformas).
Não publicar nem promover esta entrega sem nova instrução do usuário.

### Dados.10 — IBA e réplica, 24/10/2026 (em andamento)

Base: fontes selados dados.9, SHA-256
59cecf0965e3ce5f25a21c667faaea94c689f7fe90bc70632dd6458bb7c3c253.
Árvore de ensaio: `/private/tmp/santafe-dados10-e1jl697w`.
Receita reproduzível em `experimentos/dados-v10/preparar.py`, patches somente
nessa árvore. IBA3 (`santafe-3`): descritor obrigatório por DSO, validação antes
do inicializador mesmo sem checkversion, fence C, assinatura ESC SF3 e formato
0x30 do bytecode. Gerenciador identifica a IBA no cache; cinco bibC e helpers
recompilados. SDK/pkg-config corrigido para fornecer a definição candidata e
preservar caminhos com espaços. Não tratar dlopen como sandbox.

14 grupos IBA passaram no macOS, incluindo SDK C/C++ instalado, carga global,
recusa de módulos antigos e bytecode recíproco 2.1/3. Regressão de dez etapas
mais onze subetapas passou antes da correção do SDK; repetição completa com
manual/SDK final em andamento. Gerenciador passou, inclusive módulo nativo e
recuperação em seis fases. Logs de falhas de preparação preservados, não
contados como aprovação. Debian/WASM ainda não concluídos nesta anotação.

Acesso SSH rafael não lê /opt/carteiro, /etc/santafe e depósitos; sudo sem senha
não autorizado pela máquina. Foi solicitado ao usuário executar o coletor
`sudo python3 /tmp/capturar-replica-dados10.py --copiar-dados`, já enviado e
conferido. Ele somente lê produção e cria cópia privada em /var/tmp, com dump
transacional; não para serviços. Dados/segredos não devem sair do servidor.
A captura ainda não existe. Não alegar migração completa com dados sintéticos.
`unshare --user --map-root-user --net` está disponível para isolar a rede da
réplica. Próximo: concluir Debian/WASM, preparar verificação de integridade da
captura e adaptação isolada; executar migração real apenas após a captura.
Nenhuma instalação em produção, alteração de banco/serviço, publicação ou push.

### Dados.10 — evidências intermediárias e pendências

macOS x86_64 e Debian x86_64: IBA passou em 14 grupos, incluindo SDK C/C++
instalado, e regressão passou em dez etapas + onze subetapas. Gerenciador,
instalação e sete grupos de gerações/rollback passaram. macOS completou 13
percursos de aplicativos e carga de 60s. Debian repetiu 13 percursos/carga60s;
WASM recompilado passou 18 casos + recuperação. Carga Debian ampliada para180s
em execução. Nenhuma alegação de suporte Windows/ARM ou soak de horas.

Falhas encontradas nos ensaios: pkgconf Debian escapava octetos UTF-8 antes da
leitura; corrigida a análise de argumentos em octetos. O PULSO terminou a quinta
escrita depois de o cliente observar cinco recusas TLS; contador agora aguarda
até3s mantendo a exigência de todos os eventos. Relatório de carga deixava
PASSOU antes de concluir assertivas; agora registra FALHOU em qualquer exceção.
Uma carga Debian teve HTTP503 isolado; a repetição de60s passou, mas a causa
continua desconhecida. Não dar essa falha por corrigida nem promover estável.

Captura real ainda ausente. Verificador/restaurador (`experimentos/dados-v10/`)
passaram dez testes SINTÉTICOS no Debian, incluindo ambos os bancos, hashes
SQL/depósitos, corrupção, permissões, symlink/traversal e recusa sem namespace.
Corrigida a inspeção da rede para usar netlink (a montagem sysfs ainda refletia
interfaces do host). Coletor exige ambos os bancos e apenas tabelas InnoDB.
A restauração usa MariaDB exclusivo sem TCP, eventos ou destinos externos.
Isso prepara o primeiro gate; não migra/valida aplicativos reais sozinho.
A réplica privada aguarda execução do coletor com sudo pelo usuário.

Receita refeita a partir do arquivo9: zero divergências nos fontes de produto,
manual, bibliotecas, aplicativos, testes e editores da árvore ensaiada10.
Produção conferida por leitura: núcleo2.1.0 e cinco serviços ativos.
Próximo: concluir carga180s, selar pacote com gates abertos explícitos, conferir
checksum no servidor e retomar captura/restauração/migração real quando existir.

### Dados.10 — entrega de homologação confirmada, 24/10/2026

Carga Debian ampliada concluiu 180,07s com 10.555 operações HTTP medidas, 60 cartas
persistidas, 1.200 consultas DNS e 230.428KiB de RSS agregado no pico. Nenhum 503
nessa rodada; isso não esclarece a falha da primeira. A investigação permanece
explicitamente aberta em ESTADO.json. macOS: 60,10s, 1.915 operações HTTP,
199.028KiB. As evidências atuais estão aprovadas; as tentativas falhas foram
preservadas. Não promover a versão estável por esse conjunto isolado.

Entrega: `dist/santafe-candidato-dados.10-homologacao.tar.gz`
SHA-256: `25e0a08e3b83a7bf95651312e5afd6f5d2e31d32e7c3f771807a51c9ce0f7fee`.
Fontes (762): `0098b7388db7b851c00137e89ec3240f9be2b7f3e20b2bb4cd6ed00a4581af3a`.
Duas montagens idênticas. Servidor: `/tmp/santafe-dados10.v901wuit/entrega`,
162 checksums conferidos por Python e sha256sum; 415 fontes de produto/manual
idênticos à árvore Debian ensaiada. Pacotes 9 e 8 selados preservados.
Coletor remoto conferido, SHA-256
`47bf8601915195b9d0afeccfc3f683b6e98fa0f8752696b9f4893e83fae91bf9`.

Não há publicador de produção. Conferência inofensiva da entrega:
`cd /tmp/santafe-dados10.v901wuit/entrega && sha256sum -c SHA256SUMS`.

Próxima ação depende da captura real pelo usuário, já solicitada:
`sudo python3 /tmp/capturar-replica-dados10.py --copiar-dados`.
Somente então executar verificar-replica.py/restaurar-replica.py no caminho
retornado, sem baixar dados privados. Esses scripts comprovam apenas captura
íntegra/restauração; continuar a adaptação dos aplicativos reais, testes de
atualização/rollback preservando novas escritas e investigação do 503. Não
marcar a migração real concluída. Pendências e limites em
`experimentos/dados-v10/RELATORIO.md` e MIGRACAO.md. Produção permanece 2.1.0.

### Dados.11 — réplica real recebida, 24/10/2026

O operador executou o coletor. Captura privada no servidor:
`/var/tmp/santafe-replica-dados10-4vr_jg0i`, 1.841 arquivos e dois bancos.
Verificação SHA-256/permissões passou. Restauração validada em
`/var/tmp/santafe-restauro11-sbldf9cz`: 13 tabelas por banco, 212 objetos
referenciados em Santafé e 35 em Pão do Café, nenhum ausente ou divergente.
Dados, mensagens, SQL e credenciais permanecem no servidor.

Errata do harness dados.10: o hash dos objetos postais é BLAKE2b-256
(`segredo.resuma`), não SHA-256. A checagem anterior gerou falsos divergentes.
Corrigidos restaurador e fixture sintética em `experimentos/dados-v11`;
dez ensaios sintéticos repetidos passaram. O manifesto da captura continua
corretamente usando SHA-256. Não modificar a entrega selada dados.10.

Preparado `migrar-replica.py`: chroot próprio por geração, namespaces de rede,
PID e montagem; sistema operacional montado somente para leitura, bibliotecas
e aplicativos copiados, banco e depósitos privados compartilhados entre as
gerações para conferir rollback preservando novas escritas. O teste de
montagem somente leitura passou no Debian sem sudo. Produção intocada.
Não confundir restauração íntegra com aprovação da migração dos aplicativos.

O controle automático recusou imprimir fontes privados da captura no chat.
Alternativa adotada: fontes locais e comparação remota por hashes; mensagens,
configurações, erros completos e demais conteúdos privados não são exportados.
Próxima ação: executar adaptação, leitura histórica integral, escritas de teste
e retorno à geração estável na réplica. Corrigir falhas reais, registrar limites
e preparar dados.11 sem promoção estável nem instalação operacional.

### Dados.11 — migração completa ensaiada e baterias repetidas

Árvores compiladas: macOS `/private/tmp/santafe-dados11-8si4nn8u`, Debian
`/tmp/santafe-dados11-t_gq3n4g`. Base imutável dados.10, IBA3 preservada.
Regressão: dez etapas e onze subetapas nos dois sistemas; IBA/SDK 14 grupos;
instalação cinco, gerações sete, gerenciador com recuperação seis fases.
WASM reconstruído: 18 casos + recuperação. Manual: 174 exemplos, 264 contratos
C e 351 Fé; fontes de produto 183. Gramáticas/paletas repetidas, sem nova
inspeção visual das janelas (camada visual inalterada).

Réplica FINAL privada: `/var/tmp/santafe-migracao11-2okin__d`, 23 grupos aprovados.
Dois bancos/depósitos, 77 fontes finais compilados, SDK/CLI/SLS dados.11 instalados
no chroot, nginx de ambos os domínios, duas zonas DNS UDP/TCP com chaves DNSSEC
preservadas, recebedor, agência TLS, IMAP, dois Carteiros, portal e Pão do Café.
Logins e novas escritas usam contas sintéticas. Originais históricos e anexos
são conferidos por BLAKE2b-256. Ciclo estável → candidata → estável preservou
as novas escritas: 105 originais/16 anexos iniciais, 141/22 no final. Nenhuma
troca de banco de produção, serviço, catálogo, push ou etiqueta.

Carga final da réplica: seis clientes, 9.280 operações HTTP em 60,07s, sem falha.
Rodada anterior sem checagem final SLS/SDK: 10.045 em 60,03s. Não somar durações.
O 503 do primeiro teste dados.10 continua sem causa demonstrada. Demais limites:
certificados de teste; integrações externas desativadas; estáticos em leitura;
sem upload da comunidade, soak de horas, Windows/ARM ou perda elétrica real.

Defeito real encontrado na baseline: GET /entrar sem destino retornava 500 por
acesso ao valor nulo em destinoApósEntrada. Corrigido SOMENTE na candidata,
com teste exigindo 200. Também migrada a exclusão de limites expirados para
tabela.apague. A baseline reproduz o defeito ao fazer rollback, documentado.
Os erros restantes das tentativas eram de preparação do harness, preservados
nos logs; somente as rodadas concluídas entram no estado de aprovação.

Incidente de laboratório: cópias repetidas esgotaram temporariamente o disco
compartilhado. Removidas apenas cópias encerradas desta tarefa, preservando
captura original, restauração íntegra, rodada final e registros privados.
Adicionadas reserva de 2 GiB e montagem de estáticos em leitura sem duplicação.
Após a limpeza, sete serviços estavam ativos e quatro endpoints HTTPS dos
dois domínios responderam 200. Núcleo operacional continua 2.1.0. Essa evidência
pontual não prova ausência de falhas transitórias durante o esgotamento.
Última medição de espaço: 2,88 GiB livres após limpeza das rodadas anteriores.

Relatório exportável: `evidencias/replica11-real.json` dentro da árvore Debian;
foi criado por seleção de contagens/resultados. Não copiar SQL, snapshots,
mensagens, configurações ou logs privados ao Mac/pacote. Compilar/selar apenas
fontes públicos e evidências sanitizadas. Próximo: comparar reprodução limpa,
selar entrega dados.11 e conferir SHA-256 no diretório de homologação do servidor.
Não há publicador de produção; promoção estável permanece bloqueada pelos
gates de `experimentos/dados-v11/ESTADO.json`.

### Dados.11 — entrega selada e conferida no servidor

Reprodução limpa e árvore ensaiada geraram os mesmos 778 fontes. SHA-256:
`5ff4e9f68f512e964f0401c7722c3fc9581ac74c3bbd99b7587ed4e3018f0c31`.
O relatório distingue chaves sintéticas de teste de segredos de produção;
nenhum conteúdo privado da réplica foi exportado. Foram retirados da entrega
os pacotes intermediários usados para gerar os editores; os únicos instaladores
oferecidos são VS Code experimental 0.0.11 e SantafeDados 0.0.11 para Sublime.

Entrega local: `dist/candidato-dados-v11`, com 88 arquivos conferidos pelo
manifesto (89 incluindo SHA256SUMS). Pacote de homologação:
`dist/santafe-candidato-dados.11-homologacao.tar.gz`, 3.674.687 bytes, SHA-256
`33c88a5d48990fe293648d49d2748dee7c766632df165b6dd15c543d55f65b07`.

Cópia extraída e validada no servidor:
`/tmp/santafe-dados11-t_gq3n4g/entrega`. Os 88 checksums passaram; 584 arquivos
de produto/testes/manual corresponderam exatamente à árvore Debian ensaiada.
O conteúdo de ambos os instaladores correspondeu aos kits ensaiados no Debian.
Nenhum instalador de produção foi executado. Conferência inofensiva:

```sh
cd /tmp/santafe-dados11-t_gq3n4g/entrega && sha256sum -c SHA256SUMS
```

Próximas pendências para a promoção estável: reproduzir/investigar o HTTP 503
isolado de dados.10, soak prolongado com orçamento de recursos e ensaios das
integrações externas ainda não cobertas. Evitar novas cópias integrais sem
verificar o espaço: o incidente de disco e seus limites estão registrados no
relatório. Dados.11 está pronto para homologação, não para promoção estável.

### Dados.12 — investigação e carga prolongada em andamento

Terminologia definida pelo usuário: alternativa (fallback), reversão (rollback),
retorno (callback); função de retorno quando for necessário distinguir do valor.
Registrada em docs/TERMINOLOGIA.md; comandos SQL/APIs externas preservados.

Árvores novas: macOS /private/tmp/santafe-dados12-6doadl8p; Debian
/tmp/santafe-dados12-zz4m7fc1, derivadas do fonte selado dados.11 SHA-256
5ff4e9f68f512e964f0401c7722c3fc9581ac74c3bbd99b7587ed4e3018f0c31.
Nenhuma instalação de produção. Réplica dados.11 reutilizada em
/var/tmp/santafe-migracao11-2okin__d; registros anteriores preservados em
registros-dados11. Evitou duplicar banco/depósitos.

HTTP 503 reproduzido no laboratório sintético /tmp/santafe-apps5-w6hxpari:
Error on delete of /tmp/#sql-temptable-…MAI, Errcode 2. O evento ocorreu
às 18:02:06 UTC, um segundo após nova inicialização de MariaDB da réplica.
Ambos usavam /tmp. O código MariaDB 10.11 mysql_rm_tmp_tables limpa #sql*
na inicialização. Prova negativa/positiva em testar-temporarios.py passou:
compartilhar diretório privado remove sentinela; separar preserva. Nenhum
ensaio adversarial remove arquivos no /tmp público. A ocorrência original
dados.10 não preservou corpo/causa; a reprodução identifica o mecanismo sem
inventar evidência histórica. Correção: --tmpdir exclusivo em bootstrap e
servidores de ensaio, conferido por SELECT @@tmpdir.

Primeira tentativa de carga da réplica interrompida: monitor lia /proc do host,
registrando RSS zero. Corrigido para proc do namespace, com recusa de amostra
vazia. Segunda tentativa de reinício recusou registro parcial em vez do original;
corrigido uso do registro preservado. Terceira interrompida para corrigir tmpdir.
Nenhuma dessas tentativas conta como aprovação.

Rodada válida iniciada com registro /tmp/dados12-replica-r4.log: alvo 3600s,
6 leitores, no máximo 12 pedidos/s, prioridade reduzida, reserva livre 2 GiB,
crescimento do filesystem <=256 MiB, RSS agregado <=800 MiB, memória disponível
>=768 MiB, registros <=128 MiB e descritores <=2048. Monitor a cada 5s.
Resultado e mensagens continuam privados no servidor; exportar apenas contagens
e consumo. INTERROMPER-DADOS12 no laboratório solicita parada limpa. Não
considerar conclusão antes de resultado-dados12.json PASSOU e duração >=3600.

Regressões de núcleo/SLS/gramáticas, IBA, gerenciador e gerações passaram nos
dois sistemas. A primeira tentativa macOS usou binário instalado antigo sem -P
e referência dados.11 no lugar de dados.7; corrigidas referências e repetida
com src/santafé 2.1.0 e /private/tmp/santafe-dados7-hx7q0pf7/src/santafé.
Carga sintética corrigida de 600s e WebAssembly ainda em andamento.

Dados.12, continuação: WebAssembly passou 18 casos e recuperação após erro.
Carga sintética corrigida passou 600,07s e 40.373 operações HTTP, mais SMTP,
IMAP e DNS. Roteiro genérico de integração postal completo passou no macOS e
Debian após a separação de tmpdir (logs dados12-integracao-postal-*).

Rodada r4 interrompida: o monitor contava registros ativos, mas não os
rotacionados. A reserva de disco continuava respeitada. Registros preservados
em registros-tentativa4; não contar como aprovação. Corrigido contador para
somar todos os arquivos em candidata/var/log. Rodada r5 iniciada em 18:16 UTC,
com a hora completa novamente, log /tmp/dados12-replica-r5.log. Não reduzir a
janela nem aceitar resultado parcial. Resultado final deverá ter 12 grupos,
três leituras de conteúdo, novas escritas preservadas e >=3600s monitorados.

Removidos somente bancos sintéticos encerrados de dados12 (178 MiB do ensaio
HTTP e 180 MiB da integração genérica), com shutdown confirmado e ausência
de processo usando o datadir. Logs preservados. Não remover captura original,
restauração ou réplica real de trabalho. Relatório/estado dados12 ainda são
rascunhos e não estão aprovados para homologação até a conclusão da carga.

Rodada r5 interrompida: a soma de RSS/descritores precisava incluir também os
filhos nginx. Corrigido para todos os processos do namespace (inclui executor),
com nova rodada r6 às 18:22 UTC, /tmp/dados12-replica-r6.log, sessão local 35540.
Conferência independente por namespace PID visto do host passou: 13 processos,
315568 KiB/250 descritores versus monitor 315548 KiB/249 na amostra próxima.
Evidência pública monitor12.json. R5 preservada em registros-tentativa5.
A duração requerida continua 3600s inteiros nesta rodada. Sem alterar produção.

À metade da rodada r6: 1946s, 23346 pedidos, RSS agregado ~315 MiB,
2776 MiB livres e ~48 MiB de registros. Nenhum erro HTTP. Não aprovar ainda.

O controle automático recusou transferir um arquivo amplo de JSON/logs, por
não haver prova de segurança de cada conteúdo. Alternativa concluída sem
nova autorização: exportar-publicos.py confere uma lista explícita com rótulos
fixos locais (rotulos-publicos.json), contagens, hashes e marcadores constantes;
não copia linhas de logs nem texto livre. Os 13 resultados sanitizados (9351
bytes) foram aceitos e estão em /private/tmp/dados12-resultados-sanitizados.json,
materializados em /private/tmp/dados12-coleta/evidencias/debian. Os registros
completos permanecem no servidor. Exportar-evidencias.py também foi reforçado
com a ordem fixa dos 12 grupos, fases/versão fixas e métricas exclusivamente
numéricas antes de exportar a réplica final. Não transferir o arquivo amplo
/tmp/dados12-evidencias-publicas-parciais.tar.gz; foi protegido com modo 0600.

Rodada r6 concluída com PASSOU: 3600,39s, 43176 requisições HTTP, seis leitores,
p95 54,89ms e 719 amostras. RSS máximo 323624 KiB, disco livre mínimo 2748 MiB,
registros incluindo rotações até 71441690 bytes, descritores até 265.
Os 12 grupos passaram; 141 originais/22 anexos antes, 153/24 após novas escritas,
e os mesmos 153/24 preservados após reversão. Nenhum HTTP 503 na rodada válida.
Fonte da evidência: replica12-real.json, exportado com rótulos fixos e métricas.

Produção: núcleo 2.1.0 com SHA-256 inalterado; mesmos sete processos/instantes
de início; quatro endpoints HTTPS 200. Resumo sanitizado producao12.json.
Conteúdo dos dois kits de editores idêntico macOS/Debian: 47 entradas.
Evidências reunidas em /private/tmp/dados12-coleta. Falta somente sincronizar
documentação final, repetir comparação dos fontes, selar e conferir a entrega
no servidor. Nenhuma promoção estável, instalação, publicação externa ou push.
