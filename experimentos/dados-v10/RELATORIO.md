# Homologação dados.10 — 24/10/2026

**Candidato preparado; promoção estável bloqueada. RÉPLICA REAL PENDENTE.**
Não houve instalação em produção, troca de serviços, migração de banco real,
publicação de catálogos, push ou tag. A instalação operacional foi conferida
por leitura: Santafé 2.1.0, portal, IMAP e os dois Carteiros ativos.

## Implementação

- IBA 3, identidade `santafe-3`, descritor obrigatório em cada DSO. Recusa antes
  do inicializador mesmo quando não existe chamada `luaL_checkversion`.
- Novo fence numérico C, assinatura ESC SF3 e versão 0x30 do bytecode. Núcleo 2.1,
  Lua e candidatos anteriores não são bibliotecas/bytecodes intercambiáveis.
- Cinco bibliotecas C e helpers SLS/gerenciador recompilados. Identidade do cache
  nativo inclui IBA e formato de bytecode.
- SDK/pkg-config fornece a definição experimental e protege caminhos com
  espaços; teste com cabeçalhos instalados em C e C++.
- Captura privada com dois bancos transacionais, inventário e SHA-256; verificador
  de integridade/permissões e restauração em namespace sem rede externa. O
  cruzamento de objetos das cartas, anexos e filas recusa depósitos incompletos.
- Manual candidato e contrato de dados atualizados. Mantidas sintaxe/semântica
  de dados.9 e correção visual do VS Code; kits 0.0.10/SLS 1.0.0-dados.10.

A IBA confere compatibilidade acidental, não confiança: a carga nativa já pode
executar construtores. Bytecode também não é formato seguro para entrada externa.
Detalhes em IBA.md e MIGRACAO.md.

## Execuções concluídas

| Bateria | macOS 15.7.7 x86_64 | Debian 12 x86_64 |
|---|---|---|
| IBA/SDK C/C++/bytecode/cache | 14 grupos | 14 grupos |
| Regressão dados.10 + anterior | 10 etapas + 11 subetapas | 10 + 11 |
| Colares e fontes migrados | 14 grupos / 183 fontes | 14 / 183 |
| Persistência ONFÉ | 17 grupos | 17 grupos |
| SLS e sincronização | completos na bateria | completos na bateria |
| Manual | 174 compilações, 12 execuções, 264 contratos C, 351 Fé | mesmos critérios |
| Gerenciador e módulo nativo | passou; recuperação em 6 fases | passou; recuperação em 6 fases |
| Instalação privada e falhas/rollback | 5 grupos, prefixo com espaços | 5 grupos |
| Gerações atômicas | 7 grupos | 7 grupos |
| Aplicativos/protocolos | 13 percursos | 13 percursos |
| Carga final | 60,10s; 1.915 operações HTTP medidas | 180,07s; 10.555 operações HTTP medidas |
| Pico de RSS agregado dos processos de ensaio | 199.028KiB | 230.428KiB |
| SMTP / DNS na carga | 60 cartas persistidas / 1.200 consultas | mesmos volumes |
| WebAssembly reconstruído | executado no Debian | 18 casos + recuperação |
| Captura/restauração adversarial sintética | exige namespace Linux | 10 grupos |

Gramáticas/paletas: 612 entradas; TextMate 25+45, Sublime 17+7 e Prism 5, nos
dois sistemas. Não foi repetida inspeção de pixels/hosts com kit 10. A inspeção
real do candidato 9 continua sendo a evidência da camada visual inalterada;
esta revisão não deve ser descrita como nova aprovação visual dos editores.

Na troca de gerações, os leitores Debian observaram candidata e estável;
os leitores macOS só observaram estável. O ensaio cobre300 leituras/20 trocas;
não aumentar a conclusão além disso. Baseline apenas núcleo 2.1: não é rollback
dos aplicativos reais com mensagens recebidas após a atualização.

## Falhas preservadas e correções

1. Asserção antiga de IBA esperava falha no inicializador, mas o carregador agora
   recusa antes; corrigida para validar a recusa antecipada. Um identificador de
   teste `e` era reservado; corrigido, com regressão repetida.
2. `pkgconf` Debian escapava cada octeto UTF-8; a leitura textual do harness
   falhava antes da compilação. O harness desfaz quoting nos octetos, sem shell,
   e só depois decodifica. SDK C/C++ repetidos nos dois sistemas.
3. A escrita do quinto evento PULSO terminava depois da quinta recusa TLS. A
   prova confirmou cinco eventos no arquivo. O teste aguarda até 3s mantendo a
   exigência original. Não foram afrouxados os limites do servidor.
4. O relatório de carga podia deixar PASSOU antes da última asserção. Agora
   somente marca PASSOU ao concluir e marca FALHOU em qualquer exceção. A
   tentativa original está preservada e não conta como aprovação.
5. O sysfs montado no host mostrava interfaces antigas dentro do namespace.
   A verificação agora usa netlink e exige somente loopback. Os dez testes
   sintéticos repetidos passaram, incluindo recusa fora do namespace.
6. **HTTP 503 intermitente, ainda aberto:** primeira carga Debian teve uma resposta
   503 em /carteiro/entrada. Repetições de 60s e 180s passaram. O teste agora
   preserva corpo/status da falha para investigação. A causa não foi confirmada;
   não declarar corrigido por repetição aprovada. O primeiro log e o PULSO
   sintético continuam no laboratório do servidor.

## O que impede a promoção

- Falta capturar e migrar a instalação real completa; o acesso rafael não pode
  ler diretórios protegidos sem sudo. O operador precisa executar o coletor já
  conferido em `/tmp/capturar-replica-dados10.py`. Nenhuma captura real existe
  no momento deste relatório. Restauração sintética não substitui essa etapa.
- Falta resolver/investigar o HTTP 503 e executar soak prolongado e ensaios do
  ciclo operacional com as configurações/dados copiados.
- Falta comprovar rollback preservando escritas posteriores à migração real.
- Não foram ensaiados Windows/ARM nem perda elétrica real. Definir plataformas
  oficialmente cobertas antes da promoção, sem extrapolar x86_64/macOS/Debian.

ESTADO.json registra explicitamente a impossibilidade de promover esta entrega
como estável. Os instaladores públicos do candidato continuam bloqueados.

## Reprodutibilidade e evidência

Base imutável dados.9:
`59cecf0965e3ce5f25a21c667faaea94c689f7fe90bc70632dd6458bb7c3c253`.
Receitas em experimentos/dados-v10, fontes de produto comparados com uma nova
aplicação da receita sem divergências. MANIFESTO-FONTES.json cobre cada fonte;
SHA256SUMS cobre a entrega. Binários usados nos testes têm hashes registrados
em evidencias/{macos,debian}/binarios10.json. Logs incluem tentativas falhas.
Nenhum snapshot real, segredo ou banco operacional é incluído na entrega.
