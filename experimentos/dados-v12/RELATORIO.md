# Candidato dados.12 — isolamento e carga prolongada

Candidato pronto para homologação, com carga prolongada e reversão concluídas.
Consultar ESTADO.json e as evidências. Não instalar em produção.

## Alterações

O candidato deriva do fonte selado dados.11, SHA-256
`5ff4e9f68f512e964f0401c7722c3fc9581ac74c3bbd99b7587ed4e3018f0c31`.
Mantém a IBA `santafe-3`, as listas sem metatabelas e os delimitadores brutos
`[=[...]=]` e `[==[...]==]`. Não acrescenta funcionalidades da linguagem.
O SLS identifica-se como `1.0.0-dados.12`; os kits privados dos editores usam
`0.0.12`, fora dos catálogos públicos.

Os servidores MariaDB dos ensaios agora recebem um diretório de temporários
exclusivo, também durante a criação inicial do banco. A consulta `@@tmpdir`
confere o isolamento. A correção inclui o laboratório de aplicativos e o
roteiro genérico de integração postal. Não foi aplicada uma tentativa
automática para esconder respostas HTTP 503.

A terminologia adotada está em `docs/TERMINOLOGIA.md`: alternativa, reversão
e retorno. As ocorrências explicativas no manual foram atualizadas; comandos
SQL, identificadores externos e entregas históricas seladas foram preservados.

## HTTP 503

Na reprodução dados.12, a resposta de `/carteiro/entrada` continha um erro de
remoção de arquivo temporário SQL `.MAI`, com código de sistema 2, arquivo
inexistente. A falha coincidiu com o início de outra instância MariaDB do
laboratório. Ambas usavam `/tmp` para temporários.

O código oficial do MariaDB 10.11 limpa arquivos com prefixo `#sql` no diretório
temporário durante a inicialização. A prova controlada desta entrega confirmou
que uma sentinela no diretório compartilhado é removida e que o diretório
exclusivo a preserva. O ensaio adversarial utiliza apenas diretórios sintéticos
privados, sem tocar nos temporários SQL do host.
Referências: [limpeza de temporários](https://raw.githubusercontent.com/MariaDB/server/10.11/sql/sql_base.cc)
e [inicialização do servidor](https://raw.githubusercontent.com/MariaDB/server/10.11/sql/mysqld.cc).

`diagnostico503.json` guarda o resumo e o hash da resposta sintética;
`temporarios12.json` guarda a prova de remoção/preservação. A ocorrência original
de dados.10 não preservou o detalhe do erro, portanto sua causa exata permanece
sem comprovação retrospectiva. Não confundir essa limitação com a reprodução
efetivamente identificada e corrigida nesta revisão.

## Ensaios e limites

Foram repetidas as regressões no macOS e no Debian x86_64: dez etapas e onze
subetapas, instalação em cinco grupos, IBA/SDK em 14 grupos e operações de
troca/reversão em sete grupos. Núcleo, ONFÉ, SLS incremental, manual, gerenciador
e gramáticas dos editores passaram. O WebAssembly foi reconstruído no Debian:
18 casos e recuperação após erro passaram.

O roteiro genérico Correio/MariaDB/Carteiro também passou integralmente nos
dois sistemas, com temporários exclusivos: fila, conteúdo HTML isolado,
triagem local, quarentena, recuperação, cópia e restauração.

Os ensaios de gramática não equivalem a uma nova inspeção visual das janelas.
Não houve mudança semântica nas gramáticas nesta revisão; somente atualização
da identificação dos kits. Não há nova aprovação visual dos editores.

O conteúdo dos dois kits foi comparado entre macOS e Debian: as 47 entradas
foram idênticas, desconsiderando somente metadados do arquivo ZIP.

A réplica completa aprovada anteriormente foi reutilizada sem duplicar bancos
nem depósitos. Santafé e Pão do Café conservam seus bancos independentes.
O Pão do Café continua sendo consumidor externo, sem seus fontes nesta entrega.
Os processos da réplica executam em namespaces de rede, PID e montagem, sem
rota externa, com certificados de teste e prioridade reduzida.

A carga longa exige uma hora efetiva, seis leitores e limite agregado de
12 pedidos por segundo. Mede recursos a cada cinco segundos e interrompe se
violar qualquer orçamento: disco livre abaixo de 2 GiB, crescimento acima de
256 MiB, memória agregada dos processos acima de 800 MiB, memória disponível
do host abaixo de 768 MiB, registros acima de 128 MiB ou mais de 2.048
descritores. O teste sintético corrigido exige dez minutos adicionais.

Após a hora de leitura HTTP, o roteiro testa novas escritas, SMTP com TLS,
IMAP, filas, compositor, entrada e retorno à geração estável da réplica,
conferindo os conteúdos antigos e novos. O validador mantém explícito o defeito
já registrado em dados.11: `/entrar` sem destino retorna 500 na réplica 2.1.0;
a candidata deve retornar 200. Não é uma hora de carga simultânea
em todos esses protocolos. Nenhuma mensagem é enviada à rede externa.

SQL, cartas, anexos, credenciais e registros privados permanecem no servidor.
A exportação inclui apenas resultados, contagens e métricas de recursos.
Os registros Debian na entrega são resumos sanitizados com marcadores de
conclusão e hashes dos originais, que permanecem no servidor. Uma transferência
ampla foi recusada pelo controle automático; a exportação por lista explícita,
sem texto livre nem linhas de registros, foi aceita.

## Tentativas não aprovadas

A primeira carga da réplica foi interrompida porque o monitor lia o `/proc`
do host e registrava RSS zero. A segunda recusou um registro parcial no lugar
da evidência original. A terceira foi interrompida para separar os temporários.
Essas tentativas não contam como aprovações. O monitor atual consulta o `/proc`
do namespace e recusa amostras sem processos visíveis.

A quarta rodada foi interrompida ao identificar que o contador de registros
ignorava os arquivos rotacionados. A reserva de disco permaneceu respeitada,
mas essa rodada também não vale como aprovação. O monitor corrigido soma todos
os arquivos do diretório de registros e a quinta rodada recomeça a hora inteira.

A quinta rodada foi interrompida para incluir os processos filhos do nginx
na soma de memória e descritores. A sexta rodada usa todos os processos do
namespace. Uma conferência independente pelo host confirmou os 13 processos
e a correspondência das métricas, sem contar processos de produção.

A primeira regressão macOS usou referências incorretas de executáveis;
foi repetida com o núcleo estável 2.1.0 e a referência dados.7 corretos.
Uma conferência de sintaxe Python tentou usar o cache global sem permissão;
foi substituída pela análise em memória, que passou. Nenhuma dessas falhas foi
ocultada como sucesso.

## Resultados finais

A rodada r6, válida após cinco tentativas interrompidas, concluiu 3.600,39 segundos, com 43.176 requisições
HTTP e seis leitores. Nenhum HTTP 503 reapareceu. O percentil 95 foi de
54,89 ms; isso caracteriza este ensaio, sem promessa de capacidade em produção.
Foram registradas 719 amostras de recursos. Pico de RSS agregado:
323.624 KiB (316,04 MiB);
menor espaço livre: 2.748 MiB;
registros, incluindo rotações: até 68,13 MiB;
descritores: até 265. Todos os orçamentos foram respeitados.

As leituras conferiram 141 originais e 22 anexos antes das novas escritas.
Após SMTP, IMAP, filas, compositor e entrada, a candidata e a geração revertida
preservaram os mesmos 153 originais e 24 anexos. Os 12 grupos da réplica passaram.
A carga sintética corrigida completou 600,07 segundos e
40.373 operações HTTP, além dos testes SMTP, IMAP e DNS.

Na conferência operacional final, os sete serviços mantinham os mesmos processos
e instantes de início da conferência anterior. Quatro endpoints públicos
responderam 200 e o executável 2.1.0 conservava o mesmo SHA-256. Não houve
instalação do candidato nem reinício operacional.

## O que falta para a versão estável

Esta entrega não autoriza promoção estável. Continuam fora da homologação:
renovação de certificados públicos, retransmissor externo, antimalware,
triagem e autenticação DNS externa, upload da comunidade e falha elétrica real.
O suporte estável a Windows/ARM ainda precisa de escopo e validação próprios.
Os limites restantes estão registrados em ESTADO.json; esta entrega não
comprova esses cenários externos nem permite promover a versão estável.

Não houve instalação, reinício de serviços de produção, publicação de catálogos,
push ou criação de etiqueta. O núcleo operacional permanece na linha 2.1.0.
