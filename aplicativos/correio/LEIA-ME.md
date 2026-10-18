# Serviços do Correio

**Estado estável:** Correio 1.0.0, incluindo o acesso IMAP 1.2.0.

Esta árvore reúne os processos do sistema postal. A biblioteca reutilizável
está em `bibs/bibf/correio.fé`; estes programas ligam a biblioteca ao
diretório MariaDB, ao depósito, à fila e ao PULSO.

```text
servidor remoto --SMTP--> Recebedor --> CD --> Antivírus --> SPF/DKIM/DMARC
                                                   |                    |
                                                   +------ Triagem <----+
                                                              |
                                                        caixa local
Carteiro -----------------------------> CD + Antivírus --> fila --> Envios --> MX
```

## Componentes

- **Recebedor** (`recebedor.fé`): escuta SMTP/SMTPUTF8, valida destinatários
  locais e só confirma uma carta depois de persistida. Não autentica usuários
  na porta 25. A primeira carta destinada a um usuário ativo provisiona sua
  caixa de maneira idempotente, sem exigir acesso anterior ao Carteiro.
- **CD** (`correio.cd`): Centro de Distribuição chamado como módulo; aplica
  regras, consulta o antivírus, entrega localmente e cria postagens na fila.
- **Antivírus** (`correio.antivírus`): cliente Santafé assíncrono do `clamd`;
  transmite o MIME completo por `INSTREAM` antes de qualquer persistência.
- **Autenticação postal** (`correio.autenticação`): avalia SPF, verifica todas
  as assinaturas DKIM e aplica DMARC antes da Triagem. Rejeição de identidade
  produz SMTP 550; DNS temporariamente indisponível produz SMTP 451.
- **Envios** (`envios.fé`): reserva uma carta pendente, tenta transportá-la e
  consulta o MX de cada domínio, tenta as alternativas por prioridade e
  registra entrega, falha definitiva ou nova tentativa. Também cria avisos
  estruturados de atraso/falha e separa itens corrompidos em quarentena. Um
  retransmissor continua disponível como rota configurável quando a entrega
  direta sofre bloqueio de reputação. A operação atual pode usar o Mailjet em
  `in-v3.mailjet.com:587`, com STARTTLS, SMTPUTF8 e autenticação, mantendo as
  credenciais somente em `/etc/santafe/mailjet.env`. Nesse caminho, a parte
  local Unicode é preservada, mas o domínio dos endereços no envelope e nos
  campos postais do cabeçalho segue em A-label/Punycode, exatamente como foi
  validado no transportador. O objeto guardado pelo Depósito e a apresentação
  do Carteiro continuam em Unicode.
- **Fila**: estado durável entre CD e Envios; não é outro processo.

O processo **Correio Agência** (`agência.fé`) recebe submissão autenticada nas
portas 587 e 465. A 465 usa TLS desde o primeiro taco e é a preferência para
novos clientes; a 587 exige `STARTTLS` antes de anunciar `AUTH PLAIN`. O
Recebedor continua reservado à porta 25 e nunca vira retransmissor aberto.

A Agência usa as mesmas contas do portal e do Carteiro. Depois de autenticar,
o usuário só pode empregar a própria caixa tanto no envelope `MAIL FROM`
quanto no cabeçalho visível `From`. Os destinatários podem ser externos; a
mensagem passa pelo antivírus, fica registrada em `Enviadas` e entra na mesma
fila durável usada pelo Carteiro. O caminho reverso vazio (`MAIL FROM:<>`) é
preservado para avisos de falha, mas o autor visível continua vinculado à
conta autenticada.

Endereços SMTPUTF8 conservam a parte local e o domínio em Unicode no fluxo
direto e no objeto postal guardado. Assim, `josé@santafé.dev.br` continua
escrito dessa forma no Carteiro. Punycode fica restrito ao DNS, à identificação
técnica do servidor e à representação de transporte exigida por um
retransmissor externo. Mensagens sem endereços internacionais continuam usando
palavras MIME para nomes ou assuntos Unicode quando necessário.

Uma palavra MIME nunca é um endereço. A Agência recusa palavras codificadas
dentro da parte local, `Message-ID` codificado e o caractere de substituição
`U+FFFD`, pois nesses casos o cliente já perdeu ou deslocou a identidade. O
servidor não tenta adivinhar o texto original.

## Compatibilidade de clientes

Homologação realizada em 1º de setembro de 2026:

| Cliente ou serviço | Situação | Resultado observado |
|---|---|---|
| Apple Mail no macOS | Homologado | IMAP/TLS, SMTP/TLS, pastas, corpos e endereços Unicode funcionam. |
| Mail no iOS | Homologado | Pastas, leitura, envio e apresentação Unicode funcionam. |
| Carteiro | Homologado | Opera nativamente com as caixas, Unicode, anexos e proteções Santafé. |
| Gmail para iOS | Sem suporte | Pode trocar caracteres acentuados do destinatário por `?` ou emitir tacos não UTF-8 nos cabeçalhos. A Agência recusa o endereço malformado com SMTP 501. |
| Gmail para Android | Incompatível | Rejeita conta com parte local Unicode; com usuário ASCII e servidor em Punycode, autentica, mas não conclui corretamente SMTPUTF8. |
| Serviço Gmail entre servidores | Compatível | Entrega e recebe cartas do Correio; a limitação pertence aos aplicativos móveis configurados como clientes externos. |

O Correio nunca interpreta `?` como curinga nem tenta reconstruir um endereço
que o cliente já corrompeu. Essa adivinhação poderia entregar a carta a outra
pessoa. A Agência recusa o endereço malformado e registra a ocorrência no
PULSO.

Conteúdo MIME ou cabeçalhos UTF-8 malformados recebem `550 5.6.0`: repetir
a mesma sequência perdida não pode corrigir a carta. Falhas reais de banco,
Depósito ou antivírus continuam temporárias e recebem `451`.

Em ensaios externos, `santafé.dev.br` e `xn--santaf-gva.dev.br` representam o
mesmo domínio. `santaf.dev.br`, sem o “é”, é outro domínio e possui SPF,
DMARC e MX independentes. Uma ferramenta sem tratamento correto de
SMTPUTF8/IDNA pode remover silenciosamente o acento e consultar essa grafia
errada mesmo quando o fonte bruto conserva o envelope e o cabeçalho Unicode.
Nesse caso, confira o fonte e consulte o Punycode; não publique registros DNS
para o domínio corrompido. Em 1º de setembro de 2026, o mail-tester atribuiu
6/10 por esse falso diagnóstico, embora DKIM, SPF, DMARC, MX, PTR e as listas
de bloqueio estivessem corretos para a identidade Santafé.

No envelope SMTP, a parte local pode chegar entre aspas conforme o RFC 5321.
`<"josé"@xn--santaf-gva.dev.br>` é validado e normalizado para
`josé@xn--santaf-gva.dev.br`, sem alterar o caractere Unicode.

O processo **Correio IMAP** (`imap.fé`) apresenta as caixas a clientes
externos pela porta 993, sempre com TLS desde a conexão. Usa a mesma conta do
portal. Credenciais ASCII podem usar `LOGIN` ou `AUTH PLAIN`; um usuário ou
senha Unicode precisa usar `AUTH PLAIN`, como determina o contrato IMAP.
Expõe `INBOX`, `Enviadas`, `Rascunhos`, `Arquivadas`, `Indesejadas` e
`Lixeira`, mantendo o
MIME no Depósito e UIDs persistentes por pasta no MariaDB. A leitura parcial
de `FETCH` evita transferir uma carta ou anexo inteiro quando o cliente pede
somente um intervalo. Durante `IDLE`, chegada, remoção e mudança de
sinalizadores são anunciadas ao cliente no intervalo configurado.
`APPEND` grava rascunhos e cópias enviadas pelo mesmo caminho assíncrono do
Depósito/MariaDB, preserva a data interna e devolve `APPENDUID`. Uma cópia
idêntica já criada pela Agência não é duplicada em `Enviadas`. A capacidade
`Arquivadas` é anunciada com o atributo especial `\\Archive`, permitindo que
clientes IMAP e o Carteiro compartilhem o mesmo destino de arquivamento.
As ações em lote do Carteiro para marcar como lida ou não lida atualizam os
mesmos sinalizadores persistidos que os clientes IMAP consultam.
`UIDPLUS` também permite `UID EXPUNGE`: fora da Lixeira, o expurgo move a carta
para ela; dentro da Lixeira, `EXPUNGE`, `UID EXPUNGE` e `CLOSE` removem a carta
definitivamente e devolvem o espaço à cota da caixa. Os objetos do Depósito
são recolhidos separadamente, somente depois de confirmar que nenhuma carta
ainda os referencia.
`COPY` e `UID COPY` conservam a carta original, os sinalizadores, a data interna
e os anexos, reservam novos UIDs no destino e devolvem `COPYUID`. O conjunto é
copiado de forma transacional e os objetos imutáveis do Depósito permanecem
compartilhados por referência.
O sinalizador `\Deleted` fica conservado no MariaDB. Assim, um cliente móvel
pode marcar a carta numa conexão e expurgá-la em outra sem que o Carteiro volte
a apresentá-la entre as duas operações.
As respostas `LIST` respeitam o padrão solicitado pelo cliente e anunciam os
atributos padronizados de uso especial; `INBOX` é reconhecida pelo próprio
nome, sem o marcador inexistente `\\Inbox`. Isso mantém a descoberta de caixas
compatível com Apple Mail e clientes IMAP estritos.
Além de `SASL-IR`, `ID` e `UNSELECT`, o servidor anuncia `ENABLE` e
`UTF8=ACCEPT`. Clientes capazes confirmam o contrato com
`ENABLE UTF8=ACCEPT`; clientes IMAP comuns também podem selecionar pastas sem
esse passo. `APPEND` internacional pode usar o literal8
`UTF8 (~{tamanho} ... )`; a forma comum também é aceita quando os cabeçalhos
contêm Unicode íntegro. Depois da ativação, `SEARCH` não aceita `CHARSET`,
porque a sessão inteira já opera em UTF-8. O servidor continua recusando
caracteres perdidos e nunca fabrica substitutas impossíveis de responder.

## Operação

### Isolamento entre plataformas

Cada plataforma conserva identidades, sessões, caixas, cartas, filas e
objetos em banco e depósito próprios. Os portões SMTP 25/465/587 e IMAP 993
podem atender mais de um domínio, mas `correio.multibanco` escolhe o destino
pelo domínio do destinatário ou da conta autenticada. Um identificador de
caixa recebe uma marca interna do banco para impedir colisão entre chaves
numéricas iguais; essa marca nunca aparece no endereço nem no MIME.

Configure o banco principal por `CORREIO_BANCO_PREFIXO` (o padrão é
`SANTAFE`) e os demais em `CORREIO_BANCOS_ADICIONAIS`, no formato
`domínio|PREFIXO|depósito`. As credenciais de cada prefixo usam
`PREFIXO_MARIADB_HOST`, `PREFIXO_MARIADB_PORTA`,
`PREFIXO_MARIADB_USUARIO`, `PREFIXO_MARIADB_SENHA` e
`PREFIXO_MARIADB_BANCO`.

Uma transação SMTP de entrada aceita destinatários de somente um banco.
Quando o remetente mistura plataformas no mesmo envelope, o segundo banco
recebe uma resposta temporária para ser reenviado separadamente. Essa regra
evita confirmação parcial e cartas duplicadas. Cada banco também possui seu
próprio `correio-envios` e sua identidade DKIM.

Copie `operação/correio.env.exemplo` para `/etc/santafe/correio.env`, preencha
as credenciais e restrinja a leitura ao administrador e ao grupo dos serviços.
O esquema está em `banco/estrutura.sql` e reutiliza `usuarios` e `sessoes`.

Crie o depósito compartilhado antes de iniciar os serviços. O `setgid` faz os
novos subdiretórios herdarem o grupo `correio`; o Carteiro participa desse
grupo por `SupplementaryGroups=correio`:

```bash
sudo install -d -o correio -g correio -m 2770 /var/lib/santafé/correio
```

Na estrutura v2, MIME, anexos e conteúdo da fila ficam em objetos imutáveis no
disco; o MariaDB guarda metadados e resumos. Para uma instalação v1, aplique
primeiro `banco/migracao-2-deposito.sql`. Depois execute, uma única vez e
com os serviços configurados, a migração retomável:

```bash
/usr/local/bin/santafé /opt/correio/migrar-depósito.fé
```

A ferramenta processa uma linha por vez, só limpa o `LONGBLOB` depois da
gravação durável e pode ser executada novamente após uma interrupção.

A estrutura v3 acrescenta o estado necessário para entrega parcial por
domínio. Aplique `banco/migracao-3-entrega-direta.sql` numa instalação v2. A
lista pendente é reduzida depois de cada aceitação, impedindo que uma nova
tentativa duplique cartas já recebidas por outro domínio.

A estrutura v4 acrescenta `responder_para` para o Carteiro respeitar
`Reply-To`. Aplique `banco/migracao-4-carteiro.sql` numa instalação v3.

A estrutura v5 conserva `classificacao_triagem`, `pontuacao_suspeita` e os
motivos explicáveis da decisão. Aplique `banco/migracao-5-triagem.sql` numa
instalação v4.

A estrutura v6 conserva os resultados SPF, DKIM e DMARC, o domínio do autor,
a política e a ação aplicada. Aplique
`banco/migracao-6-autenticação.sql` numa instalação v5.

A estrutura v7 acrescenta a decisão pessoal por carta, regras por endereço
ou domínio e um histórico de auditoria. Aplique
`banco/migracao-7-triagem-pessoal.sql` numa instalação v6. A classificação,
a pontuação e os motivos automáticos continuam imutáveis: a preferência
pessoal decide somente a pasta de entrega.

A estrutura v8 acrescenta `falhas_internas`, a quarentena da fila e o registro
idempotente `correio_avisos_entrega`. Aplique
`banco/migracao-8-confiabilidade.sql` numa instalação v7. O registro único
por fila e tipo impede que uma reinicialização duplique um aviso. A reversão
estrutural, destinada apenas a uma retirada controlada da versão, está em
`banco/reverter-8-confiabilidade.sql`.

A estrutura v9 acrescenta `uid_imap` e `correio_pastas_imap`. Aplique
`banco/migracao-9-imap.sql` numa instalação v8 antes de iniciar o acesso
IMAP. O contador de cada pasta é reservado dentro da mesma transação que
grava ou move a carta; assim UIDs não colidem nem são reutilizados.

A estrutura v10 acrescenta `apagada_imap`. Aplique
`banco/migracao-10-imap-apagadas.sql` numa instalação v9. O sinalizador
`\Deleted` passa a sobreviver ao encerramento da conexão, enquanto mover a
carta para outra pasta o limpa para evitar uma exclusão acidental posterior.

A estrutura v11 separa `remetente`, o autor visível extraído do cabeçalho
`From`, de `remetente_envelope`, o valor técnico recebido em `MAIL FROM`.
Retransmissores podem substituir o segundo por um endereço próprio de
retorno; esse endereço continua disponível para SPF, Triagem e auditoria, mas
não aparece como autor no Carteiro nem no envelope apresentado pelo IMAP.
Aplique `banco/migracao-11-remetente-envelope.sql` numa instalação v10.

As preferências particulares da interface possuem versão independente. A
estrutura v1 do Carteiro conserva os endereços em que cada caixa decidiu
confiar. Aplique
`banco/migracao-carteiro-1-remetentes-confiaveis.sql`; confiar nunca carrega
recursos externos automaticamente.

## Antivírus

Instale `clamav-daemon` e `clamav-freshclam`, mantenha as assinaturas
atualizadas e exponha o `clamd` somente em `127.0.0.1:3310`. O Correio usa
`CORREIO_ANTIVIRUS_ATIVO=verdadeiro` e falha fechado: uma ameaça recebe `554`;
motor ou assinaturas indisponíveis recebem `451` e podem ser tentados de novo.

No Debian com ativação de conectores pelo systemd, a escuta TCP também precisa
ser declarada em `clamav-daemon.socket`. O arquivo operacional
`clamav-daemon-santafe.conf` conserva o conector Unix e acrescenta somente
`127.0.0.1:3310`; nenhuma interface externa recebe essa porta.

O limite `StreamMaxLength` do ClamAV deve ser maior ou igual a
`CORREIO_LIMITE_MENSAGEM`. Neste servidor recomenda-se também
`ConcurrentDatabaseReload no`: reduz o pico de memória durante a atualização
das assinaturas, embora pause brevemente novas verificações durante a recarga.
Nesse intervalo o Correio devolve falha temporária, sem aceitar carta sem
inspeção.

## Triagem

Ative com `CORREIO_TRIAGEM_ATIVA=verdadeiro`. A biblioteca pura Santafé
`correio.triagem` avalia sinais estruturais, divergências de remetente,
quantidade de destinatários, anexos executáveis e sinais de fisgada. Ela não
abre nem consulta as ligações recebidas. Compara localmente o domínio aparente
com o destino real, reconhece Unicode/Punycode equivalentes, endereços IP,
credenciais escondidas na autoridade da URL, esquemas ativos e formulários.

Pedidos de senha ou código de acesso só pontuam quando combinados com uma
ligação ou linguagem de urgência. A lista curta de termos é pública no fonte;
não existe uma lista secreta de palavras "proibidas". Assim, cada ponto
corresponde a um motivo objetivo e visível ao usuário.

Por padrão, 4 pontos marcam a carta como `suspeita`, mas ainda a conservam na
Entrada; 8 pontos a movem para Indesejadas. Ajuste com
`CORREIO_TRIAGEM_LIMITE_SUSPEITA` e `CORREIO_TRIAGEM_LIMITE_INDESEJADA`.
`CORREIO_TRIAGEM_BLOQUEADOS` recebe uma lista global separada por vírgula. Um
endereço é escrito por inteiro; um domínio usa `@exemplo.org`. Não existe
permissão global baseada apenas no endereço declarado, pois um invasor poderia
falsificar essa identidade. As regras pessoais só são aplicadas depois do
antivírus e da autenticação postal.

A decisão produz `classificação`, `pontuaçãoDeSuspeita`, `pasta` e
`motivos`. O Carteiro apresenta esses dados e o PULSO registra somente
metadados. Um sinal de ritmo elevado do Vigia soma apenas um ponto e nunca
separa uma carta sozinho.

Fisgadas não recebem uma rejeição SMTP automática: quando a soma alcança o
limite de indesejada, a carta é preservada em Indesejadas para revisão. O
antivírus e a recusa de identidade continuam sendo fronteiras independentes.

Cada caixa pode criar regras pessoais de `permitir` ou `separar`, por
endereço exato ou domínio. A regra de endereço prevalece sobre a de domínio.
`permitir` entrega futuras cartas na Entrada; `separar`, em Indesejadas.
Essas regras não confiam no HTML, não desativam antivírus nem anulam
SPF/DKIM/DMARC. As alterações ficam no histórico
`correio_historico_triagem`, e o PULSO recebe somente caixa, carta, decisão e
escopo, nunca corpo ou anexo.

## Autenticação postal de entrada

Ative com `CORREIO_AUTENTICACAO_ATIVA=verdadeiro` e ajuste o prazo conjunto
com `CORREIO_AUTENTICACAO_TEMPO_LIMITE`. A implementação é assíncrona e
separa as responsabilidades:

- `correio.spf` autoriza o endereço remoto para MAIL FROM;
- `correio.dkim` confere o corpo, os cabeçalhos e a chave RSA publicada;
- `correio.dmarc` alinha SPF/DKIM ao domínio de From e descobre a política
  pela caminhada da árvore DNS;
- `correio.autenticação` coordena os três, acrescenta
  `Authentication-Results` e entrega uma decisão estruturada ao CD.

Uma carta passa no DMARC quando SPF alinhado **ou** DKIM alinhado passa. Por
isso, SPF falho sozinho não autoriza rejeição. `reject` gera SMTP 550,
`quarantine` envia para Indesejadas, `none` apenas registra e uma falha DNS
transitória gera SMTP 451 para permitir nova tentativa.

O Recebedor acrescenta uma fronteira mais forte para sua própria identidade:
todo domínio de `CORREIO_DOMINIOS_LOCAIS` declarado no cabeçalho `From`
precisa passar em SPF alinhado ou DKIM alinhado. Sem um deles, a carta recebe
SMTP `550 5.7.1` mesmo que o registro DMARC público ainda use `p=none`. Essa
regra não confia apenas no endereço do envelope e não enfraquece cartas
legítimas assinadas.

## Ensaio isolado

O ensaio completo cria um MariaDB temporário, aplica as estruturas, inicia o
Recebedor em `127.0.0.1:2525`, inicia o Carteiro em `127.0.0.1:7100`, envia
cartas nos dois sentidos e descarta todo o ambiente ao terminar:

```bash
make testar-correio-mariadb
```

Ele confere consultas preparadas, piscina, transações, autenticação postal,
persistência e apresentação dos resultados SPF/DKIM/DMARC, provisionamento da
caixa antes do primeiro acesso, SMTPUTF8, depósito de MIME e anexos, leitura
pelo Carteiro, protocolo assíncrono do antivírus, recusa SMTP de ameaça, fila
durável, aviso estruturado idempotente, quarentena recuperável e entrega pelo
Correio Envios. No macOS, procura
o `mariadb@11.4` do Homebrew; em outro ambiente, aceite a variável
`MARIADB_PREFIXO` apontando para a instalação isolada.

O marco estável acrescenta duas provas operacionais ao mesmo ambiente:

- reservas de cartas e avisos deixadas em `processando` por uma interrupção
  voltam a `pendente` depois que o arrendamento expira;
- banco e Depósito são copiados, restaurados em destinos novos e comparados
  integralmente antes que o ensaio seja aceito.

Execute toda a porta de qualidade postal com:

```bash
make testar-marco-postal
```

## Cópia e restauração

O banco da implantação atual compartilha a identidade do portal; por isso a
cópia transacional protege o banco completo e o Depósito no mesmo conjunto.
O SQL é capturado antes do arquivo do Depósito. Como os objetos são imutáveis
e são gravados antes da linha do banco, essa ordem impede que a cópia do banco
aponte para um objeto ausente. Um objeto novo e ainda não referenciado pode
sobrar no arquivo; isso é seguro.

```bash
sudo /opt/correio/operação/copiar-seguranca.sh
sudo /opt/correio/operação/verificar-copia-seguranca.sh \
  /var/backups/santafe-correio/AAAAMMDD-HHMMSS
```

A restauração sempre cria um banco e um Depósito novos. Ela nunca substitui a
produção silenciosamente:

```bash
sudo /opt/correio/operação/restaurar-copia-seguranca.sh \
  /var/backups/santafe-correio/AAAAMMDD-HHMMSS \
  santafe_correio_restaurado \
  /var/lib/santafé/correio-restaurado
```

Depois do ensaio, confira contagens, migrações e objetos. Uma troca real é
feita alterando a configuração para esses destinos durante uma janela
controlada; o restaurador não para serviços nem muda `/etc/santafe/correio.env`.

Os publicadores com nomes de versões intermediárias permanecem no repositório
como histórico de migração. Para uma instalação atual, use somente o publicador
do marco 1.0 e estas ferramentas operacionais.

| Unidade | Programa | Tipo |
|---|---|---|
| `correio-recebedor.service` | `/opt/correio/recebedor.fé` | contínuo |
| `correio-envios.timer` | ativa `correio-envios.service` | periódico |
| `correio-envios.service` | `/opt/correio/envios.fé` | uma carta por execução |
| `correio-agencia.service` | `/opt/correio/agência.fé` | contínuo, 465/587 |
| `correio-imap.service` | `/opt/correio/imap.fé` | contínuo, 993/TLS |

Use a porta 2525 apenas em laboratório. Porta 25 pública exige, além dos
testes funcionais, DNS MX/PTR, SPF, DKIM, DMARC, TLS, reputação, limites e
proteção operacional.

## Entrega direta e identidade

O modo padrão é `CORREIO_ENVIOS_MODO=direto`. Envios consulta os registros MX,
usa a porta 25, negocia TLS quando anunciado, exige SMTPUTF8 para endereços
internacionalizados e tenta MX alternativos em falhas temporárias. Respostas
SMTP 5xx são definitivas; rede, DNS e respostas 4xx voltam à fila com espera
progressiva. O padrão tenta novamente depois de 30 minutos e, em seguida, a
cada duas ou três horas. O prazo final padrão é cinco dias. Configure a
sequência por `CORREIO_ENVIOS_INTERVALOS` e o prazo por
`CORREIO_ENVIOS_PRAZO`.

## Avisos de entrega e quarentena

Depois de quatro horas sem conclusão, `CORREIO_ENVIOS_AVISO_ATRASO` cria um
aviso de atraso na caixa do remetente. Uma recusa 5xx ou o fim do prazo cria
um aviso final. Ambos usam `multipart/report` e uma parte
`message/global-delivery-status`: o texto em português serve à pessoa e os
campos `Action`, `Status`, `Final-Recipient` e `Diagnostic-Code` servem a
programas. O aviso conserva apenas os cabeçalhos da carta original, não
replica seu corpo nem seus anexos.

Nesta arquitetura, toda carta de saída nasce numa caixa local; por isso o CD
deposita o aviso diretamente nessa caixa. O identificador único
`(fila_id,tipo)` torna a operação idempotente. Avisos automáticos não entram
novamente na fila e, portanto, não formam ciclos. A Agência aceita o remetente
de envelope vazio `MAIL FROM:<>` para avisos de falha, sem abrir mão da
validação do autor visível autenticado.

Falhas de rede e recusas temporárias **não** são quarentena. Um item só é
separado quando sua estrutura persistida é inválida ou quando uma falha
interna se repete até `CORREIO_ENVIOS_FALHAS_QUARENTENA`. A fila expõe:

- `listeQuarentenaAssíncrono(limite, tratador)` para inspeção sem corpo;
- `reprocesseQuarentenaAssíncrono(identificação, tratador)` para liberar um
  item depois da correção da causa;
- `quarenteneAssíncrono(identificação, motivo, tratador)` para uma decisão
  operacional explícita.

Os avisos locais também possuem tentativas próprias; depois de
`CORREIO_ENVIOS_TENTATIVAS_AVISO`, ficam em quarentena sem impedir o restante
da fila. A política segue a estratégia de tentativas da RFC 5321 e o formato
das RFCs 3464 e 6533.

Cada mensagem direta é assinada com DKIM `rsa-sha256` e canonicalização
`relaxed/relaxed`. A chave privada não pertence ao repositório: mantenha-a em
`/etc/santafe-correio/dkim`, legível somente por `root:correio`. SPF e DMARC são
registros DNS, não bibliotecas executáveis.

Para operar publicamente, configure em conjunto:

- A: `mail.xn--santaf-gva.dev.br` para o IP do servidor;
- MX: domínio postal para `mail.xn--santaf-gva.dev.br`;
- PTR: o IP de saída de volta para o mesmo nome;
- SPF: autorização explícita do IP de saída;
- DKIM: chave pública em `<seletor>._domainkey`;
- DMARC: política e endereço de relatórios;
- TLS: certificado válido para o nome postal.

### Auditoria externa da identidade

`operação/auditar-identidade-postal.py` confere, sem enviar cartas nem ler
segredos, A/PTR, MX, DNSSEC, SPF, DKIM, DMARC, SMTPUTF8, 8BITMIME, STARTTLS,
certificado, RPKI e uma consulta básica à Spamhaus. Ele depende somente de
Python 3, `dig` e `openssl`; não requer `pip` nem `dnspython`.

```sh
python3 operação/auditar-identidade-postal.py 'santafé.dev.br' \
  --ip 143.208.252.1 \
  --seletor sf2026 \
  --nome-smtp xn--santaf-gva.dev.br \
  --prefixo-rpki 143.208.252.0/22 \
  --asn AS265132
```

Uma auditoria sem falhas comprova a configuração observável, mas não garante
aceitação por um destinatário. Classificações privadas de reputação, como a
autorização interna de IP do Gmail, não são publicadas em DNS.

Consulte a [arquitetura do ecossistema](../../docs/ARQUITETURA-DO-ECOSSISTEMA.md)
para o plano completo.
