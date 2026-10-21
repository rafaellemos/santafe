# Santafé 2.1.0 — entrega conjunta de 21/10/2026

**Estado: publicado e conferido em 21/10/2026.** Núcleo, SLS, gerenciador,
portal, manual, downloads e catálogo foram verificados após a publicação
executada pelo usuário. A instalação operacional não substitui o resultado
do GitHub Actions, consultado separadamente para o commit da etiqueta.

| Componente | Versão |
| --- | --- |
| Núcleo | 2.1.0 |
| SLS | 1.0.0 |
| Gerenciador/catálogo de bibliotecas | 1.0.0 / formato v1 |
| VS Code | 1.1.0 |
| Sublime | 1.1.0 |

## Entrega

Gabaritos Unicode (`®` e `Ⓡ`, NFC/NFD), correção do buffer de interpolação,
analisador com posições exatas, SLS semântico local e instalação de bibliotecas
por projeto. Detalhes em [SLS](SLS.md), [contrato SLS 1.0](SLS-1.0.md) e
[Bibliotecas](REPOSITORIO-BIBLIOTECAS-1.0.md).

A mudança é aditiva sobre 2.0.3; ABI C 503 e layout das bibliotecas existentes
permanecem. Ferramentas novas precisam do núcleo novo. As duas extensões usam
o mesmo SLS. Não houve alteração de bancos, Correio ou Pão do Café.

## Limites explícitos

- Transporte incremental, não parser incremental. Não há inferência completa
  de tipos, depurador DAP nem servidor semântico HTML/JS nesta entrega.
- Rename recusa situações dinâmicas/ambíguas; não modifica os arquivos sozinho.
- Limites de CPU, documento, índice e memória gerenciada não são um sandbox
  nem uma garantia de RSS constante para qualquer fonte.
- Bibliotecas C exigem confiança e compilador local. Os limites da compilação
  e a ausência de shell não tornam código nativo hostil seguro.
- Catálogo inicialmente curado, com `semver 1.0.0`. Sem upload público,
  assinaturas independentes de pacotes ou limpeza automática de gerações.
  Integridade SHA-256 depende da origem HTTPS confiável.
- Homologação de ferramentas: macOS Intel e Debian x86_64; Windows e outros
  ambientes não têm aprovação implícita. WebAssembly não instala bibliotecas.

## Evidências e publicação

As baterias funcionais, adversariais, memória, instalação isolada e WebAssembly
estão registradas em [AUDITORIA-SLS-1.0-20261021](AUDITORIA-SLS-1.0-20261021.md).
Os testes condicionais de MariaDB/DNS não executados continuam marcados SKIP.

O preflight conjunto já passou no Debian, sem sudo nem alterações operacionais:
compilação, regressão, instalação num prefixo temporário, 39/39 critérios SLS
no fonte e no instalado, bibliotecas/TLS, WebAssembly, manual e plano reversível.
Não confundir esse resultado com uma publicação ou com aprovação visual.

O ensaio real do VS Code é separado dos testes de gramática/mock. Após o usuário
fechar o aviso do Sublime, os testes nativos passaram: SLS, 175 casos de realce,
43 concatenações e 612 entradas da API. No VS Code, SLS, edição incremental,
refatoração, conclusão e realce combinado também passaram. Capturas reais dos
dois editores foram inspecionadas: gabaritos NFC/NFD em laranja sem itálico,
expressões como código, `função` ciano oblíquo, HTML/JavaScript em paleta suave
e isolamento nas concatenações e aspas. Nenhum documento pessoal foi alterado.

`docs/HOMOLOGACAO-CONJUNTA.json` registra versões, limites e evidências com
hashes; `operação/conjunto-versoes.json` marca os gates técnicos concluídos.
O lançador permite executar
`--preflight` sem sudo: compila, testa e prepara tudo em `/tmp`, sem instalar
ou reiniciar serviços. O modo de publicação fica reservado à execução do usuário.

O publicador cria backup reversível, verifica hashes, preserva releases
históricos e reinicia somente o portal `sfdev.service`. Processos operacionais
que já estejam em execução conservam seu executável até seu próximo reinício;
isso não deve ser descrito como atualização imediata de todos os serviços.
O registro Git e os catálogos de terceiros não são alterados pelo publicador.
A disponibilidade das extensões 1.1.0 no portal não implica publicação dessa
versão no Marketplace nem aprovação no canal oficial do Package Control.

## Registro da publicação e da etiqueta

A instalação publicada identificou núcleo 2.1.0, SLS 1.0.0 e gerenciador 1.0.0.
O SLS instalado passou nos 39 critérios, e a instalação de `semver 1.0.0` pelo
catálogo HTTPS foi conferida, incluindo importação, lock e uso sem rede.
Os 707 destinos do plano inicial e os 17 arquivos públicos foram conferidos.

As revisões textuais r1/r2 corrigiram o manual e a ajuda do gerenciador após
a entrega inicial, sem mudar sua lógica. A etiqueta `v2.1.0` registra esses
fontes corrigidos, os documentos de lançamento atualizados e a execução
automática do contrato completo SLS/bibliotecas no GitHub Actions.

Os TAR/ZIP e pacotes de editores originalmente publicados permanecem
imutáveis. Um pacote reconstruído desta etiqueta pode diferir em documentação
e metadados de CI; não deve substituir o arquivo público de mesmo nome.
O catálogo `semver 1.0.0` também não foi reempacotado.

| Artefato conferido | SHA-256 |
| --- | --- |
| TAR original 2.1.0 | `2075f756a689eaf54952909d6b551a82a5df127c23897ac6bf3c04d1fe3e2d64` |
| ZIP original 2.1.0 | `f89f8c1e18e6805bf0664bf5c284233dd39b29d2e7e1fd967570b9f9327599f2` |
| Manual público r2 | `020fa13b9625aa1eb40ddae1b0fcf2f1ea63df0647c82cc16c757cc582a5e881` |
| Ajuda/cliente instalado | `a1b522fdc3c292702666ef7663358d6d554d260b24399306923e1e1fa0ce5ac9` |

`HOMOLOGACAO-CONJUNTA.json` e as auditorias datadas preservam o estado anterior
à publicação, incluindo `publicado: false`; são evidências históricas, não o
estado atual da entrega. Logs e capturas locais permanecem fora do Git público.
