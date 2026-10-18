# Arquitetura do ecossistema Santafé

Este documento registra o vocabulário, as fronteiras e as decisões
arquiteturais do ecossistema Santafé. Ele distingue o que já existe, o que
está sendo organizado e o que foi deliberadamente adiado.

## Princípio geral

Cada componente deve expressar um conceito claro em português, esconder
detalhes de infraestrutura e cooperar por interfaces pequenas. Um componente
pode ser reutilizável sem que todos os seus adaptadores sejam obrigatórios.

### Marco histórico da primeira implantação

Este quadro registra a implantação anterior, não o inventário de versões
instaladas hoje. As versões dos aplicativos, do protocolo IMAP e da linguagem
são independentes. Para a candidata da linguagem 2.0.2, consulte a auditoria
`AUDITORIA-2.0-20261017.md`; não deduza uma atualização do servidor a partir dela.

| Componente | Versão/estado comprovado |
| --- | --- |
| Nomes | contrato 1; autoridade UDP/TCP com DNSSEC ativa |
| Correio | 1.1.0; Recebedor, Envios, Agência e IMAP ativos |
| Carteiro | 1.3.5; núcleo e interface web ativos sobre Caminheiro |
| PULSO | contrato 1; destinos locais ativos |
| Vigia | 0.1.0; integrado ao Correio |
| Autenticação postal | 1.1.0; SPF, DKIM, DMARC e identidade local |
| Triagem | 1.1.0; regras pessoais e sinais iniciais de fisgada |

Esse quadro registra capacidades comprovadas, não uma promessa de
compatibilidade eterna. Novas versões precisam conservar ensaios de migração,
reversão e integração antes da publicação.

```text
Rede sustenta a comunicação.
Nomes nomeia e localiza serviços pelo protocolo DNS.
Caminheiro conduz pedidos HTTP.
Correio transporta cartas.
Carteiro apresenta caixas e cartas ao usuário.
PULSO comunica acontecimentos.
Forte observa e protege.
O futuro servidor HTTP/HTTPS substituirá a borda atual; seu nome definitivo
está entre Átrio e Pórtico.
```

## Componentes

### Rede

**Estado:** existente.

Motor assíncrono de comunicação. Fornece conectores, resolução de nomes do
sistema, TLS, HTTP, agendamentos e laço de eventos. Não conhece zonas DNS,
rotas de aplicação, cartas ou páginas.

### Nomes

**Estado:** contrato 1; autoridade autoritativa ativa em produção e
resolvedor instalado, deliberadamente desabilitado.

Biblioteca Santafé que implementa as mensagens do protocolo DNS, zonas,
autoridade UDP/TCP, resolução iterativa desde a raiz, memrap por TTL, ACL
IPv4/IPv6 e limites contra abuso. Não usa libknot, BIND ou Unbound; Rede
fornece apenas o transporte e o laço assíncrono genérico.

O autoritativo é público. O recursivo nasce fechado em `127.0.0.0/8` e
`::1/128`; blocos do ASN precisam ser acrescentados explicitamente. ACL,
limite por origem, teto de consultas e respostas de até 1232 tacos reduzem
abuso, mas o roteamento ainda deve aplicar BCP 38/uRPF.

Os processos são separados porque têm fronteiras de confiança diferentes:

```text
Internet ── UDP/TCP :53 ──> autoridade de Nomes ──> zonas administradas
rede interna/ASN ─────────> resolvedor de Nomes ─────> hierarquia DNS pública
```

DNSSEC autoritativo com DNSKEY, RRSIG, NSEC e DS já está implementado. As
transferências de zona e a atualização dinâmica permanecem etapas posteriores.
Enquanto não houver validação DNSSEC no resolvedor e ensaio prolongado de
carga, o recursivo é destinado a laboratório e redes controladas.

#### Identidade do bloco da Telemulti

O bloco `143.208.252.0/22` pertence ao ASN da **Telemulti**. A autoridade
reversa usa `sn1.telemulti.net.br` e `sn2.telemulti.net.br` — “servidor de
nomes” —, mesmo que o
programa que os serve continue sendo Nomes, escrito em Santafé. A zona do
primeiro `/24` permanece `252.208.143.in-addr.arpa.`; o domínio institucional
identifica os servidores, não renomeia a zona definida pelo protocolo DNS.

Isso não obriga todos os PTRs a terminarem em um domínio da Telemulti. Cada IP
deve apontar para o nome canônico do serviço que realmente presta. Enquanto
`143.208.252.1` for a identidade SMTP de `santafé.dev.br`, seu PTR deve
continuar coerente com esse nome, o `A` correspondente e o nome apresentado no
SMTP. Endereços de roteadores, concentradores e infraestrutura própria podem
usar nomes da Telemulti. Endereços não utilizados não precisam ter PTR.

Decisão consolidada: a titularidade da autoridade reversa é apresentada pela
Telemulti. A migração conserva a chave DNSSEC e o DS, publica os novos nomes
nos dois servidores antes da troca da delegação e mantém temporariamente os
nomes antigos como registros de transição.

### Caminheiro

**Estado:** existente.

Arcabouço servidor de aplicações HTTP construído sobre Rede. Reconhece um
caminho, escolhe a rota e chama seu tratador. Caminheiro não depende do Nginx.

> Caminheiro conduz cada pedido HTTP pela rota correspondente até seu
> tratador.

### Correio

**Estado:** 1.0.0; Recebedor, Envios, Agência e acesso IMAP ativos.

Sistema postal de transporte. Abrange SMTP, SMTPUTF8, MIME, TLS, recebimento,
postagem, armazenamento durável, fila e envio. O núcleo não expõe SQL ao
programador; adaptadores escondem MariaDB, arquivos ou outro armazenamento.

O Correio pode funcionar sem Carteiro, como servidor postal sem interface web.

### Correio Recebedor

**Estado:** primeira implementação ativa em produção e conservada em
`aplicativos/correio/recebedor.fé`.

Recebe cartas de outros servidores pela porta SMTP. Consulta o diretório
postal, aplica limites e entrega o conteúdo durável ao Correio CD.

O autor apresentado ao usuário vem do cabeçalho RFC 5322 `From`. O remetente
técnico recebido no envelope RFC 5321 `MAIL FROM` é preservado separadamente
para SPF, Triagem, devoluções e auditoria. Assim, um endereço de retorno criado
por um retransmissor nunca toma o lugar do autor no Carteiro ou no IMAP.

Nome definitivo do processo e do programa:

```text
correio-recebedor.service
aplicativos/correio/recebedor.fé
```

### Correio CD

**Estado:** módulo dedicado disponível como `correio.cd`.

CD significa **Centro de Distribuição**. Confere, separa e determina o destino
da carta:

- consulta caixas, endereços e domínios;
- resolve apelidos e redirecionamentos;
- aplica cotas e regras;
- evita destinatários duplicados;
- encaminha para caixa local, fila de envios ou quarentena;
- emite acontecimentos PULSO.

Inicialmente será um módulo chamado pelo Recebedor e pelo Carteiro, não outro
processo. Quando o volume justificar, poderá tornar-se
`correio-cd.service` sem mudar seu contrato.

### Correio Envios

**Estado:** primeira implementação ativa em produção e conservada em
`aplicativos/correio/envios.fé`.

Retira cartas da fila de envios, transporta-as a outros servidores, registra
sucesso ou falha e agenda novas tentativas. A confiabilidade postal v8
acrescenta recuo configurável, avisos idempotentes de atraso e falha e
quarentena para registros estruturalmente irrecuperáveis.

Nome definitivo do processo e do programa:

```text
correio-envios.service
aplicativos/correio/envios.fé
```

A fila não é um processo. O CD produz entradas; Correio Envios as consome.

### Carteiro

**Estado:** 1.0.0; núcleo postal `carteiro` separado do adaptador web Caminheiro.

Arcabouço postal voltado ao usuário. Lista, abre, pesquisa, organiza, responde
e posta cartas; também entrega anexos autorizados e apresenta imagens
matriciais seguras. Não implementa SMTP.

O núcleo do Carteiro pode ser usado programaticamente sem Caminheiro. A
interface gráfica atual usa Caminheiro:

```text
carteiro.service
├── núcleo do Carteiro
└── adaptador Caminheiro
```

Sem Caminheiro não há páginas web, mas o núcleo ainda pode servir futuramente
a um cliente de terminal, gráfico ou móvel.

> Correio transporta e conserva. Carteiro apresenta e organiza.

### PULSO

**Estado:** existente.

Protocolo Unificado de Leituras, Sinais e Operações. Os serviços produzem
acontecimentos locais desde já. Quando o Forte existir, ele será acrescentado
como consumidor sem tornar os produtores dependentes dele.

### Vigia

**Estado:** biblioteca 0.1.0 existente e integrada ao Correio.

Braço local dos serviços para proteção na camada de aplicação. Cada serviço
usa o Vigia com seu próprio contexto, aplica limites e bloqueios imediatamente
e publica acontecimentos pelo PULSO. O Vigia funciona sem o Forte e não cria
sentinelas. O Correio já usa uma instância única para limites de conexão SMTP;
a incorporação ao Caminheiro, Carteiro e Nomes permanece como ampliação.

### Forte

**Estado:** futuro.

Arcabouço de observação, decisão e mitigação. Consumirá PULSO, agregará
telemetria e poderá comandar atuadores de rede, inclusive FRR/BGP, sob regras
autenticadas e auditáveis.

Seus operários serão os **sentinelas**: componentes especializados que
acompanham o PULSO de cada serviço ou domínio e trabalham coordenadamente sob
o Forte. Esse nome fica reservado à arquitetura do Forte; não faz parte do
Vigia.

```text
Serviço → Vigia → PULSO → Sentinela → Forte
Serviço ← Vigia ← PULSO ← operação do Forte
```

### Nginx

**Estado:** infraestrutura de produção atual.

Servidor de borda e proxy reverso. Termina HTTPS, escolhe o processo pelo
domínio ou caminho, serve arquivos estáticos e aplica limites de entrada.
Nginx não faz parte da fila postal e não é dependência do Caminheiro.

```text
Internet
   ↓
Nginx :80/:443
   ├── /          → sfdev + Caminheiro :7000
   ├── /carteiro → Carteiro + Caminheiro :7100
   └── /estático → arquivos no disco
```

SMTP na porta 25 vai diretamente ao Correio Recebedor, não ao módulo HTTP do
Nginx.

### Porteiro (nome provisório)

**Estado:** futuro e desnecessário para a ativação postal atual.

**Nome em avaliação:** `Átrio` ou `Pórtico`. Não renomear nem criar uma API
pública antes da decisão final.

Projeto em Santafé que poderá substituir o Nginx como servidor de borda. Para
isso deverá oferecer HTTPS, SNI, proxy reverso com fluxo contínuo, arquivos
estáticos, cache, limites, proteção contra conexões lentas, balanceamento,
WebSocket, recarga sem interrupção, ACME, PULSO e, futuramente, HTTP/2 e
HTTP/3.

> Porteiro controla quem entra; Caminheiro conduz o pedido dentro da
> aplicação.

## Fluxos postais

### Carta recebida da internet

```text
Internet
   ↓ SMTP
Correio Recebedor
   ↓
Correio CD
   ↓
caixa postal
   ↓
Carteiro
   ↓ HTTP pelo Caminheiro
usuário
```

### Carta postada pelo usuário

```text
usuário
   ↓
Carteiro
   ↓
Correio CD
   ↓ coloca na fila
[fila de envios]
   ↓ consome
Correio Envios
   ↓ SMTP
Internet
```

Os colchetes indicam armazenamento durável, não processo.

## Diretório postal e usuários

Correio consulta um **diretório postal** durante `RCPT TO` para saber se o
destinatário existe. O diretório é uma interface, não SQL público:

```santafé
diretório:existeDestinatário(endereço, tratador)
diretório:caixaDoUsuário(usuário, tratador)
```

Autenticação não pertence ao CD. A Agência consulta o adaptador de identidade
postal, que confere a conta do portal e devolve sua caixa:

```santafé
repositório:autentiqueCaixa(nome, senha, resumoIsca, tratador)
```

O Recebedor da porta 25 não autentica usuários; ele valida destinatários e
aplica as regras de recebimento entre servidores.

A implementação inicial usa a piscina assíncrona MariaDB e reutiliza as
tabelas `usuarios` e `sessoes` do site. Não haverá outra senha nem outra base
de identidades. A caixa acrescenta somente propriedades postais como endereço,
cota, uso e estado.

Ao validar o primeiro `RCPT TO` de um usuário ativo, o diretório cria sua
caixa postal de forma idempotente. Assim, a pessoa pode receber uma carta
antes mesmo de abrir o Carteiro pela primeira vez; pedidos simultâneos não
duplicam a caixa por causa das restrições únicas do esquema.

Respostas SMTP:

- destinatário confirmado como inexistente: `550`;
- diretório temporariamente indisponível: `451`;
- destinatário aceito: `250`.

LDAP foi deliberadamente adiado. Ele poderá ser outro adaptador assíncrono no
futuro, quando houver uma necessidade concreta de integração empresarial.

## Depósito postal

A implementação usa um modelo híbrido:

```text
MariaDB
├── usuários e caixas
├── endereços e domínios
├── metadados, pastas e pesquisa
└── fila e estado da entrega

Disco
└── objetos imutáveis identificados pelo resumo do conteúdo
```

Diretórios previstos:

```text
/var/lib/santafé/correio/
└── objetos/
    └── ab/
        └── cd/
            └── abcdef...  # resumo criptográfico completo
```

Tabelas da primeira estrutura do adaptador oficial MariaDB:

```text
correio_migracoes
correio_caixas
correio_cartas
correio_anexos
correio_fila
```

Apelidos, redirecionamentos e vários endereços por caixa acrescentarão
`correio_enderecos` quando esse recurso entrar. Nesta primeira estrutura, cada
caixa tem um endereço principal.

MIME, anexos e conteúdo da fila são gravados pela biblioteca C `arquivo`, fora
do laço principal, antes de a transação MariaDB passar a referenciá-los. O
MariaDB conserva um resumo criptográfico de 64 algarismos e os metadados. O
mesmo conteúdo ocupa um único objeto físico, mesmo quando é referenciado pela
carta e pela fila. Toda leitura confere tamanho e resumo.

Registros da estrutura v1 que ainda tenham `LONGBLOB` continuam legíveis. A
ferramenta `aplicativos/correio/migrar-depósito.fé` os converte, uma linha
por vez, e pode ser retomada. Ela não é executada automaticamente. Objetos que
ficarem órfãos por uma interrupção antes da confirmação SQL são inofensivos;
uma coleta futura poderá removê-los comparando o depósito com as referências.

O esquema e suas migrações acompanharão o adaptador. O processo SMTP não
receberá permissão para criar ou alterar tabelas silenciosamente. A instalação
aplica migrações explicitamente; o serviço apenas confere a versão.

Antes de responder `250` ao final de `DATA`, o Recebedor deve garantir a
gravação durável da carta. A indisponibilidade do MariaDB não pode provocar
perda nem rejeição permanente incorreta.

## Fila de envios

A fila pertence ao sistema Correio e forma a fronteira entre CD e Envios:

```text
CD:       cria estado pendente
Envios:   reserva, processa, entrega, adia, avisa ou encerra com falha
Operador: inspeciona a quarentena e libera o item depois de corrigir a causa
```

Falhas SMTP temporárias continuam pendentes; recusas definitivas geram aviso
final; somente corrupção ou falha interna repetida entram em quarentena. Não
existirá `correio-fila.service`.

## Correio Agência

**Estado:** ativo e validado nas portas 465 e 587.

A Agência recebe submissão autenticada para clientes externos, como
Thunderbird e Outlook. A porta 465 usa TLS implícito; a 587 exige STARTTLS.
Ela reutiliza a conta e a caixa do portal, confere o remetente do envelope e
o autor visível, aceita destinatários externos e entrega a mensagem ao mesmo
CD, antivírus, depósito e fila usados pelo Carteiro. O Carteiro web continua
podendo postar diretamente no CD sem atravessar SMTP.

## Correio IMAP

**Estado:** versão 1.2.0 implementada e validada contra clientes IMAP4rev1,
incluindo a descoberta estrita de caixas usada pelo Apple Mail, na porta 993.

O processo `correio-imap.service` apresenta as mesmas caixas do Carteiro a
clientes como Thunderbird, Apple Mail e aplicativos móveis. Usa TLS desde o
primeiro taco, a mesma identidade Argon2id do portal e o mesmo repositório
MariaDB/Depósito. Não existe porta 143 nem autenticação aberta.

As pastas fixas são `INBOX`, `Enviadas`, `Rascunhos`, `Arquivadas`,
`Indesejadas` e `Lixeira`, com os atributos de uso especial correspondentes.
O Carteiro acrescenta a visão virtual `Todas`, que reúne as cartas conservadas
sem duplicá-las nem expor uma pasta IMAP artificial. A estrutura
postal v9 atribui UIDs persistentes por pasta e nunca reutiliza um UID depois
de mover uma carta. Leitura, pesquisa, sinalizadores, MIME original, anexos e
movimentação para Arquivadas/Indesejadas/Lixeira estão cobertos.

O `FETCH` aceita leitura parcial por origem e quantidade, para que clientes
móveis não precisem transferir integralmente cartas e anexos grandes. O
`APPEND` persiste Rascunhos e cópias em Enviadas com o MIME original, cota,
data interna e UID na mesma transação; uma repetição idêntica em Enviadas é
deduplicada. `UIDPLUS` fornece `APPENDUID`, `COPYUID` e `UID EXPUNGE`. `COPY` e
`UID COPY` preservam origem, sinalizadores, data interna e anexos, mas atribuem
novos UIDs no destino dentro da mesma transação. O expurgo retira a
carta da pasta selecionada, mas a política postal ainda a conserva na
Lixeira. Esta etapa não permite criar/renomear pastas. O comando `IDLE` anuncia
chegada, remoção e mudança de
sinalizadores sem exigir consulta do cliente. A movimentação obedece à política do Carteiro: Entrada e Enviadas
não se misturam; cartas separadas podem voltar apenas à pasta coerente com
sua direção.

A versão 1.2.0 anuncia `SASL-IR`, `ID`, `UNSELECT`, `ENABLE` e `UTF8=ACCEPT`.
Clientes capazes confirmam o contrato com `ENABLE UTF8=ACCEPT`; clientes IMAP
comuns também podem selecionar pastas sem esse passo, desde que preservem os
endereços SMTPUTF8. Os aplicativos Gmail móveis não estão homologados como
clientes externos porque corrompem ou recusam identidades Unicode em caminhos
de submissão.
Credenciais Unicode usam `AUTHENTICATE`. Rascunhos internacionais entram por
`APPEND UTF8` ou por `APPEND` comum quando seus cabeçalhos forem Unicode válido.
Formas irrecuperáveis — como U+FFFD,
parte local codificada como palavra MIME ou `Message-ID` codificado — são
recusadas explicitamente, nunca adivinhadas. As linhas de controle permanecem
US-ASCII; os cabeçalhos e literais MIME preservam o Unicode original.

## Implantações externas e escalabilidade

Empresas, marcas e domínios que usam Correio ou Carteiro não fazem parte do
projeto Santafé. Mesmo quando compartilham uma máquina por economia, pertencem
a projetos, bancos, depósitos, identidades, configurações e ciclos de publicação
independentes.

O núcleo conhece apenas contratos genéricos. Uma implantação informa domínio,
prefixo de configuração, banco, depósito, identidade DKIM e políticas sem
introduzir nomes de clientes no fonte da plataforma. Sites, marcas, cadastros
empresariais, gerência e publicadores particulares vivem fora deste
repositório.

Compartilhar os portões SMTP/IMAP é uma opção de implantação, não uma
dependência. Um cliente pode ser deslocado para outro servidor sem alterar o
contrato do Correio ou do Carteiro e sem migrar dados dos demais. O caminho
escalável exige:

- processos web e trabalhadores replicáveis, sem sessão indispensável no
  sistema de arquivos local;
- reserva atômica de trabalhos e filas compartilhadas;
- bancos independentes ou fragmentos escolhidos por configuração;
- depósitos substituíveis e isolados por implantação;
- limites do Vigia por serviço, domínio, identidade e caixa;
- chaves, certificados, cópias de segurança e observação independentes;
- publicação da plataforma separada da publicação de cada cliente.

O contrato operacional completo está em
[`ESCALABILIDADE-E-IMPLANTACOES.md`](ESCALABILIDADE-E-IMPLANTACOES.md).

## Fronteiras públicas

Correio e Carteiro não expõem comandos SQL. O programador pede operações do
domínio e o adaptador decide como realizá-las:

```santafé
postal:guardeCarta(carta, tratador)
postal:enfileireCarta(carta, tratador)
carteiro:listeCartas(caixa, pasta, tratador)
carteiro:obtenhaCarta(caixa, identificação, tratador)
carteiro:movaCarta(caixa, identificação, pasta, tratador)
carteiro:obtenhaAnexo(caixa, carta, anexo, tratador)
```

Somente o autor de um adaptador MariaDB, LDAP ou outro armazenamento escreve
as consultas correspondentes.

## Segurança de conteúdo

Carteiro nunca executa automaticamente uma carta ou anexo:

- texto pode ser apresentado diretamente;
- HTML precisa ser higienizado;
- PNG, JPEG, GIF e WebP podem ser visualizados com tipo correto e autorização;
- PDF continua como anexo para baixar até existir um visualizador isolado;
- SVG exige higienização ou entrega como download;
- formatos desconhecidos são oferecidos para baixar.

O antivírus automático é uma integração assíncrona: `correio.antivírus`
transmite o MIME completo ao processo isolado ClamAV antes da persistência ou
da fila. Ameaças são recusadas; indisponibilidade gera falha temporária. O
motor e as assinaturas são externos, mas decisão, telemetria e continuidade do
fluxo pertencem ao Correio Santafé.

A pasta Indesejadas e a **Triagem 1.1** explicável estão implementadas em
`correio.triagem`. A biblioteca pura Santafé avalia sinais estruturais,
regras globais de bloqueio e indícios de fisgada, calcula
`pontuaçãoDeSuspeita`, conserva os motivos e emite acontecimentos PULSO sem
expor o corpo. Ela reconhece ligações mascaradas, destinos por IP,
credenciais na URL, formulários e esquemas ativos sem visitar o destino.
Cartas suspeitas permanecem na Entrada; somente as que alcançam o limite de
indesejada são separadas automaticamente.

SPF, verificação DKIM e DMARC formam a camada de autenticação postal de
entrada e precedem a Triagem. Cada caixa possui regras pessoais posteriores
por endereço ou domínio; a regra exata prevalece e decide somente entre
Entrada e Indesejadas, sem apagar a avaliação automática. A decisão fica
auditada e gera PULSO sem conteúdo da carta. Reputação externa continua
futura. Limites SMTP, Antivírus e retransmissão fechada tratam riscos
distintos e não substituem autenticação nem Triagem.

### Alfândega postal

**Estado:** conceito futuro em avaliação.

`Alfândega` fica anotado como possível nome da inspeção postal profunda. A
decisão de produto permanece aberta: ela pode ser a lapidação da própria
Triagem ou uma camada separada, consumida pelo Correio depois da autenticação
postal. Nenhuma API deve receber esse nome antes de essa fronteira ficar
comprovada pelo uso.

O escopo candidato inclui:

- motor de regras versionadas, testáveis e distribuídas com assinatura;
- reputação de endereços, domínios e ligações consultada assincronamente
  por meio de Nomes;
- aprendizagem estatística baseada nas decisões explícitas dos usuários,
  preservando motivo e possibilidade de auditoria;
- inspeção aprofundada de MIME, HTML, imagens, PDF e arquivos compactados;
- tratamento controlado de redirecionadores e ligações encurtadas, sem
  transformar o recebimento SMTP em navegação irrestrita;
- medição de falsos positivos e falsos negativos sobre um acervo de ensaio.

A Alfândega não substituirá o Antivírus, que procura código malicioso; a
autenticação postal, que verifica identidade; o Vigia, que limita abuso em
tempo real; nem o PULSO, que transporta acontecimentos. Sua metáfora é
inspecionar procedência, apresentação e risco da carga postal antes da
entrega final.

## Coleções: listas, tabelas e índices esparsos

**Estado:** decisão aplicada no núcleo.

Uma tabela serve tanto a listas quanto a mapas. O operador `#t`
mede somente a parte de lista contínua, iniciada no índice `1`; não é uma
contagem de todas as chaves e não é confiável quando há buracos. Essa medida
estrutural deve permanecer barata e será a semântica de
`tamanho(tabela)`. Para colares, `tamanho` continua
contando grafemas visíveis.

Não será acrescentada uma verificação automática de esparsidade a
`#` nem a `tamanho`: percorrer a tabela inteira teria
custo linear em uma operação cotidiana. Quando a aplicação precisar saber se
uma tabela é uma sequência válida, ela deverá pedir essa verificação
explicitamente.

`tabela.maiorÍndice(t)` informa a maior chave numérica positiva; não
conta entradas e não define ordem de inserção. O nome histórico
`tabela.maiorN` foi removido antes da versão maior. Uma futura
`tabela.quantidade(t)`, se o uso justificar, contará todas as
chaves presentes com custo linear e sem mudar as regras de listas.

## Ativação em etapas

1. organização local e separação de responsabilidades: concluída;
2. Correio Recebedor, CD, Envios e núcleo do Carteiro: implementados;
3. adaptador web Caminheiro: implementado;
4. depósito híbrido MariaDB + arquivos e testes unitários: concluído;
5. ensaio integrado SMTPUTF8 → CD → depósito → Carteiro: concluído;
6. validar com MariaDB isolado em `127.0.0.1:2525` e `127.0.0.1:7100`:
   concluído, incluindo o caminho de Envios;
7. ativar a interface `/carteiro/` pelo Nginx;
8. entrega direta por MX, assinatura DKIM e identidade DNS: implementadas e
   operacionais;
9. autenticação de entrada SPF/DKIM/DMARC: implementada, persistida e
   apresentada no Carteiro.
10. Triagem pessoal, auditável e explicável por caixa: implementada.
11. proteção da identidade local e reconhecimento inicial de fisgadas:
    implementados na Autenticação 1.1 e na Triagem 1.1.
12. avisos de entrega, recuo SMTP configurável e quarentena recuperável:
    implementados e comprovados no ensaio MariaDB isolado.
13. retomada de reservas expiradas depois de interrupção: implementada e
    comprovada para cartas e avisos.
14. cópia e restauração de banco e Depósito em destinos isolados:
    implementadas e comparadas integralmente no marco 1.0.

O Correio envia diretamente ao MX do destinatário. Um servidor SMTP de saída
configurado permanece disponível somente como contingência. A reputação
postal própria será construída gradualmente depois da publicação dos registros
de identidade e da ativação controlada do tráfego.

## Mapeamento da primeira implementação

| Primeira implementação | Arquitetura definida |
|---|---|
| `aplicativos/correio/recebedor.fé` | Correio Recebedor |
| validação e distribuição no repositório | Correio CD |
| `aplicativos/correio/envios.fé` | Correio Envios |
| `aplicação.fé` e `páginas.fé` | Carteiro web |
| `correio.filaMariaDB` | fila durável inicial |

Essa mudança preserva o fluxo funcional que já foi testado; ela corrige
nomes, propriedade dos componentes e o depósito antes da publicação.
