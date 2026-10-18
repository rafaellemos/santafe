# Marco Correio e Carteiro 1.0

Este marco congela o primeiro contrato estável do ecossistema postal Santafé.
Ele não declara o correio eletrônico um problema encerrado para sempre; declara
que as capacidades abaixo possuem contrato, documentação e ensaios repetíveis.

## Contratos congelados

- `correio` 1.0.0: MIME, SMTP/SMTPUTF8, recepção, submissão, entrega direta,
  fila, avisos, quarentena e integração com Depósito/CD;
- `correio.imap` 1.0.0: TLS 993, pastas fixas, UIDs, leitura parcial, MOVE,
  IDLE, APPEND, UIDPLUS e Unicode;
- `carteiro` 1.0.0: listar, pesquisar, abrir, organizar, responder,
  encaminhar e postar cartas, anexos autorizados, HTML isolado e regras
  pessoais da Triagem;
- Recebedor, Envios e Agência como processos separados;
- MariaDB para metadados e objetos imutáveis no Depósito;
- Antivírus fechado em caso de falha, autenticação SPF/DKIM/DMARC, Triagem
  explicável e limites locais pelo Vigia.

## Porta de qualidade

`make testar-marco-postal` precisa concluir sem falhas. A porta executa:

1. conferência de versões e sintaxe das ferramentas operacionais;
2. suíte geral do Santafé;
3. MariaDB isolado com SMTP, Carteiro, CD, Depósito, fila e Envios;
4. antivírus simulado, autenticação, Triagem, fisgada e HTML isolado;
5. aviso idempotente e quarentena recuperável;
6. retomada de cartas e avisos abandonados em `processando`;
7. cópia e restauração integral do banco e do Depósito;
8. validação estrutural e sintática do manual.

## Homologação de clientes

Apple Mail no macOS, Mail no iOS e Carteiro estão homologados. O transporte
entre o Correio e os servidores Gmail também funciona. Gmail para iOS e Gmail
para Android não são clientes externos homologados: nos ensaios de 1º de
setembro de 2026, recusaram ou corromperam identidades SMTPUTF8 antes que o
servidor pudesse recuperá-las.

## Fora do marco

- reputação externa e a possível Alfândega;
- POP3 e exclusão definitiva pelo usuário;
- PULSO remoto assíncrono com TLS;
- Forte e seus sentinelas;
- sites, dados e operação de empresas que usam a plataforma.

Esses itens são evoluções e não impedem a estabilidade do contrato 1.0.
