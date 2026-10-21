# Auditoria da evolução SLS 1.0

## Fechamento dos editores — 21/10, após liberação pelo usuário

O usuário fechou o aviso do Sublime. A extensão instalada 1.1.0 carregou e
o SLS respondeu pelo cliente LSP real: navegação, referências, rename Unicode,
símbolos, formatação e tokens semânticos passaram. As suítes nativas também
passaram: 175 casos de realce, 43 concatenações (edição/limpeza, cinco temas)
e 612 entradas da API/paletas. VS Code 1.1.0/SLS 1.0.0 repetiu o host real
com sucesso; o exemplo visual recebeu 54 conclusões.

Capturas reais dos dois editores inspecionadas: gabaritos NFC/NFD em laranja
sem itálico, expressão como código, função ciano oblíquo, paleta suave HTML/JS,
concatenações e escapes sem vazamento de realce. `--[[javascript]]` é a
anotação documentada usada no fixture; não se homologou o alias `--[[js]]`.
Não foram alterados documentos pessoais nem reiniciados os editores à força.

O ensaio 4 Debian também passou integralmente: fontes/extensões finais, prefixo
isolado, 39/39 SLS em ambos os prefixos, bibliotecas, WASM, manual e publicador.
Evidências e hashes em `HOMOLOGACAO-CONJUNTA.json`; capturas/logs locais em
`docs/evidencias/conjunto-20261021`. Homologado tecnicamente, não publicado.

## Resultado anterior — 21/10, 05h20 (histórico)

Os parágrafos de “marco inicial” abaixo são históricos, não o estado atual.
O conjunto candidato passou a identificar núcleo 2.1.0, SLS 1.0.0,
gerenciador 1.0.0 e extensões 1.1.0. Não houve publicação, push ou etiqueta.

- 39/39 critérios funcionais do SLS; 24 incrementais, 24 semânticos
  adversariais e cinco de cancelamento; lexer com posições e filhos de
  gabaritos reais, sem execução do fonte.
- SLS: 900 falhas de alocação e 3.000 entradas arbitrárias; gerenciador:
  1.440 falhas de alocação; verificações de memória/descritores e sanitizadores
  passaram. Isso não prova ausência de todas as vulnerabilidades.
- Biblioteca real: SemVer com 87 critérios; resolução, TLS com certificado
  local, downgrade recusado, cache/offline, lock, instalação de C autorizada,
  integridade ao importar e recuperação de seis fases de atualização real
  1.0.0 → 1.1.0. Nenhuma instalação/execução de pacote de terceiros.
- Catálogo curado determinístico e imutável: primeiro pacote `semver 1.0.0`,
  importado/ensaiado de ponta a ponta. Endpoint ainda não publicado.
- Publicador: transação completa/parcial, rollback, edição concorrente,
  preservação de histórico e escopo restrito ensaiados em fixtures.
- Regressão macOS: código zero. MariaDB/DNS sem configuração continuam SKIP.
- Debian isolado da revisão de auditoria 5: compilação, regressão, prefixo
  com espaços, SLS instalado, bibliotecas e WebAssembly concluídos com código
  zero. Pacote SHA-256
  `7c4330631b84f0188683c1dc1bc6cc29f7ee58766a6d3529b1933d4566716713`.
  Esse pacote precede a promoção de versões e o publicador conjunto; é prova
  da revisão auditada, não dos bytes finais ainda a empacotar.
- Linux, 2 CPUs, 100 módulos/3.000 funções: p95 documento/símbolos 208,7 ms,
  hover 1,15 ms, tokens 227,55 ms, símbolos globais 567,95 ms (inclui frio),
  edição/diagnóstico 79,17 ms. RSS estabilizou em ~105 MiB no ensaio.
- Preflight conjunto repetido no Debian com versões 2.1.0/1.0.0/1.1.0:
  ensaio 3 finalizou com `CONJUNTO_PREFLIGHT_OK`, em
  `/tmp/santafe-conjunto.98wbuF8L`. Compilação, regressão, prefixo isolado,
  39/39 fonte/instalado, TLS do catálogo, WASM, manual e plano de 706 destinos.
  TAR SHA-256 `75da11d85cf7b77afb32de42d6841adb6f472d5a19b0d39fc14f3f054912e687`.
  Sem instalar ou reiniciar produção. Os fallbacks dos editores corrigidos
  depois desse ensaio requerem empacotamento/ensaio final próprios.
- VS Code Extension Host real repetido com SLS1.0.0/extensão1.1.0 e `-E -P`:
  definição, referências, rename NFC/NFD, assinaturas, formatação, tokens
  semânticos/HTML combinados e edição incremental passaram.
  Relatório `/tmp/santafe-vscode-host-sls-final-20261021.json`. Não é captura visual.
- TextMate real: 175 casos e cores Dark+/Monokai. Fallback Sublime agora
  preserva marcas combinantes nos nomes; navegação local VS Code também.
  Testes reproduziram a falha antes da correção e passaram após o ajuste.
- Sublime: o processo principal aguarda `NSAlert runModal`; CLI não progride.
  Não foi possível obter pixels/texto da janela. Não apertar botões às cegas
  nem encerrar o aplicativo com documentos abertos. Teste host/visual pendente.

Evidências locais em `/tmp/santafe-debian-bibliotecas-20261021`,
`/tmp/santafe-conjunto-regressao-20261021.log` e
`/tmp/santafe-sls-1.0.0-contrato.json`. Esses caminhos não são arquivos
distribuídos nem resultados de produção. Novos ensaios devem preservar a
procedência exata dos artefatos.

## Marco inicial (histórico)

Data: 21/10/2026. Ambiente: macOS 15.7.7, Intel, Python 3.9.6.
Base Git: `aba35374154a0cdc5ecc4d55a3fbdf327f7f3355`, com as alterações locais
da nova bateria. **Não é uma certificação nem lançamento de SLS 1.0.**

## Entregue nesta etapa

- [Contrato e ordem de implementação](SLS-1.0.md), separando o servidor de
  linguagem, os clientes, a homologação e o futuro repositório de bibliotecas.
- Cliente LSP de teste independente, com projetos/processos temporários,
  limites, timeouts e validação de posições/edições UTF-16.
- 39 critérios executáveis: 13 do perfil existente e 26 do alvo 1.0.
- 17 autotestes do verificador, incluindo capacidade anunciada mas vazia,
  limpeza de processo travado e não aprovação indevida de pendências.
- Regressão atual integrada a `testar.sh`. Workflow manual de contrato-alvo
  preparado para Ubuntu/macOS, sem dispará-lo no GitHub nesta etapa.

Não foram alterados o runtime, o fonte do SLS, as extensões, os serviços de
produção nem os artefatos públicos. Nenhum commit, etiqueta ou pacote foi enviado.

## Medição inicial

| Ensaio | Resultado |
| --- | --- |
| Bateria do perfil atual, SLS do repositório 0.1.1 | 13 OK; zero falhas/pendências |
| Bateria do contrato-alvo 1.0 | 13 OK; 1 FALHA; 25 PENDENTES |
| Autotestes do verificador | 17 aprovados |
| SLS: testes anteriores de protocolo e robustez | Aprovados |
| VS Code: teste automatizado de restart/eventos atrasados/confiança | Aprovado |
| Sublime: pacote, conclusões e recorte de linguagens embutidas | Aprovado |
| `testar.sh` | Código zero, com os testes condicionais abaixo não executados |
| Manual | 1.237 IDs; 580 funções colapsáveis; 171 exemplos; 258 contratos C e 344 Fé |
| Identidade do iniciador local `/usr/local/bin/santafé-sls` | Responde **0.1.0**; somente handshake foi conferido |

A falha do alvo é **intervalo de diagnóstico**: após um emoji, o erro precisa
selecionar o token incorreto em coordenadas UTF-16; a implementação atual informa
coluna zero. É uma limitação conhecida do perfil inicial, não regressão causada
pela bateria. As outras 25 pendências correspondem a capacidades ainda não
anunciadas pelo SLS.

`testar.sh` inicialmente parou porque o sandbox não permitia abrir uma porta
local de teste. A repetição com permissão para os ensaios locais concluiu com
código zero. Testes que exigem MariaDB, autenticação com DNS real ou chave DNSSEC
específica continuaram ignorados por ausência das respectivas configurações;
não foram declarados aprovados.

Não houve teste visual novo nos editores, teste Debian novo, atualização da
instalação do Mac ou validação em produção. A divergência entre o iniciador
instalado (0.1.0) e o fonte (0.1.1) integra o gate de distribuição. O número da
extensão não comprova qual servidor um editor está usando.

## Reprodução

```bash
python3 testes/integracao/testar_sls_infraestrutura.py
python3 testes/integracao/testar_sls_aceitacao.py --perfil atual
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 \
  --relatorio /tmp/sls-contrato-1.0.json
```

O último comando deve sair com código 1 neste marco, pois existe uma falha além
das pendências. O relatório contém procedência, hashes da bateria e do fonte,
versão respondida, critérios individuais e gates externos ainda pendentes.

Próximo marco de implementação: análise com intervalos precisos, sincronização
incremental e base de escopos. O repositório oficial de bibliotecas continua
posterior ao fechamento do SLS; não foi iniciado aqui.
