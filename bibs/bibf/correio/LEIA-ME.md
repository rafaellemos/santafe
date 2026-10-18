# Correio Santafé

O **Correio Santafé** constrói mensagens MIME e fornece cliente e servidor
SMTP assíncronos. Ele usa `rede` para TCP/TLS, `mariadb` quando se deseja uma
fila durável e `pulso` para telemetria estruturada.

Esta versão implementa o núcleo funcional do serviço. Ela não tenta
ser, sozinha, uma plataforma completa de caixas postais: IMAP e reputação
de endereço são camadas distintas. A Triagem nativa e o antivírus já se integram ao
motor ClamAV; DKIM é assinado pelo Correio, enquanto SPF e DMARC são
publicados no DNS.

## O que já funciona

- mensagens UTF-8 com texto, HTML, alternativas e anexos;
- cabeçalhos MIME, `Message-ID`, data SMTP e codificação Base64;
- proteção contra injeção de cabeçalhos e *dot-stuffing*;
- cliente SMTP por TLS implícito ou `STARTTLS`;
- entrega direta assíncrona por MX, com MX implícito e alternativas;
- TLS oportunista para transporte entre servidores;
- assinatura DKIM `rsa-sha256` em `correio.dkim`;
- autenticação `AUTH PLAIN`, somente depois de TLS por padrão;
- servidor SMTP com `EHLO`, `HELO`, `STARTTLS`, `AUTH PLAIN`, `MAIL`, `RCPT`,
  `DATA`, `RSET`, `NOOP`, `VRFY` e `QUIT`;
- limites de linha, mensagem, comandos, destinatários, conexões e tentativas
  de autenticação;
- proibição de retransmissão aberta;
- persistência confirmada antes da resposta SMTP `250`;
- fila durável MariaDB com reserva, prazo, adiamento e recuperação;
- espera SMTP configurável, avisos estruturados de atraso/falha e quarentena
  operacional recuperável;
- eventos locais PULSO sem corpo de mensagem, senha ou comando `AUTH`.
- verificação assíncrona do MIME completo antes de persistir uma entrada ou
  enfileirar uma saída, por `correio.antivírus` e ClamAV.
- proteção da identidade dos `domíniosLocais`: uma carta que declare um
  desses domínios em `From` precisa passar em SPF alinhado ou DKIM alinhado,
  mesmo enquanto o DMARC público estiver somente em observação (`p=none`).

TLS em `rede` precisa do provedor do GLib. O instalador inclui o pacote
`glib-networking` no Linux, Homebrew e MacPorts.

## Antivírus automático

`correio.antivírus` conversa com o processo isolado `clamd` pelo protocolo
`INSTREAM`. Cada trecho recebe seu tamanho de 32 ticos em ordem de rede; o
conteúdo não precisa ser gravado num arquivo temporário. A porta do `clamd`
fica restrita a `127.0.0.1`, pois o protocolo não possui autenticação própria.

```santafé
local Antivírus = importe "correio.antivírus"
local verificador = garanta(Antivírus.novo {
    endereço = "127.0.0.1",
    porta = 3310,
    limite = 50 * 1024 * 1024
})

verificador:examineAssíncrono(conteúdoMIME,
    função(resultado, falha)
        se falha então mostre("motor indisponível:", falha)
        senão se resultado.limpa então mostre("carta limpa")
        senão mostre("ameaça:", resultado.ameaça)
        fim fim
    fim)
```

No Correio CD a integração falha fechado:

- conteúdo limpo segue para o depósito ou para a fila;
- ameaça produz acontecimento PULSO e recusa SMTP definitiva `554`;
- motor indisponível produz `451`, permitindo nova tentativa sem perder a
  carta;
- o corpo nunca entra no PULSO; somente direção, tamanho, origem e nome da
  assinatura podem ser registrados.

Isso é Antivírus, não Triagem. A biblioteca `correio.triagem` calcula uma
`pontuaçãoDeSuspeita` por sinais objetivos, devolve todos os motivos e separa
somente as cartas que alcançam o limite de indesejada:

```santafé
local Triagem = importe "correio.triagem"
local selecionador = Triagem.nova {
    limiteSuspeita = 4,
    limiteIndesejada = 8,
    bloqueados = { "fraude@hostil.test" }
}

local resultado = selecionador:avalie(envelope, mensagemLida)
mostre(resultado.classificação, resultado.pontuaçãoDeSuspeita)
para _, motivo em ipares(resultado.motivos) início
    mostre(motivo.pontos, motivo.descrição)
fim
```

A Triagem também reconhece fisgadas sem abrir uma conexão externa: ligação
mascarada, URL com credencial antes do domínio, destino por IP, esquema ativo,
formulário de senha e pedido de segredo acompanhado por ligação ou urgência.
Unicode e Punycode do mesmo domínio são comparados como equivalentes. Uma
redefinição de senha legítima pode ser marcada como suspeita e continuar na
Entrada; sinais fortes combinados alcançam Indesejadas. Nada é apagado nem
recusado pelo SMTP apenas por essa pontuação.

SPF, verificação DKIM e DMARC precedem a Triagem. Regras pessoais por caixa
são aplicadas depois da avaliação automática e alteram somente a pasta; a
pontuação e os motivos originais permanecem disponíveis. Reputação externa
continua fora desta primeira versão.

## Criar uma mensagem

```santafé
local correio = importe "correio"

local mensagem = garanta(correio.novaMensagem {
    remetente = "rafael@exemplo.org",
    destinatários = { "ana@exemplo.net" },
    cópia = { "maria@exemplo.net" },
    assunto = "Relatório Santafé",
    texto = "O relatório segue anexo.",
    html = "<p>O relatório segue <strong>anexo</strong>.</p>",
    anexos = {
        {
            nome = "relatório.pdf",
            tipo = "application/pdf",
            caminho = "/srv/relatórios/hoje.pdf"
        }
    }
})
```

Campos principais:

| Campo | Uso |
|---|---|
| `remetente` | Endereço usado no cabeçalho e no envelope SMTP. |
| `destinatários` | Endereço ou lista obrigatória. |
| `cópia` | Lista visível opcional. |
| `cópiaOculta` | Lista usada somente no envelope; nunca vira `Bcc`. |
| `assunto` | Assunto UTF-8. |
| `texto` | Parte `text/plain`. |
| `html` | Parte `text/html`. |
| `anexos` | Lista com `nome`, `tipo` e `dados` ou `caminho`. |
| `cabeçalhos` | Cabeçalhos adicionais não reservados, como `In-Reply-To` e `References`. |

`mensagem:forme()` devolve a mensagem MIME completa. Texto e HTML são
codificados em Base64 com linhas limitadas; nomes de anexos usam o par
`filename`/`filename*`. Quando um endereço exige SMTPUTF8, endereços, nomes e
assunto permanecem em Unicode nos cabeçalhos. Sem SMTPUTF8, nomes e assuntos
Unicode usam palavras MIME.

Cada anexo pode ter até 25 MiB antes da codificação. Uma mensagem aceita no
máximo 25 anexos e 25 MiB somados. A mensagem MIME de saída, já com a expansão
Base64, tem limite de 40 MiB. O caminho em `anexo.caminho` ainda usa leitura
síncrona; em servidores, carregue o conteúdo com a biblioteca `arquivo` antes
de chamar `novaMensagem` e forneça-o por `dados`.

### Ler uma mensagem MIME

O Carteiro usa `correio.leiaMensagem(conteúdo)` para interpretar o conteúdo
bruto recebido depois de `DATA`:

```santafé
local lida, falha = correio.leiaMensagem(conteúdoMIME)
garanta(lida, falha)

mostre(lida.remetente, lida.assunto)
mostre(lida.texto ou "(sem parte de texto)")

para _, anexo em ipares(lida.anexos) início
    mostre(anexo.nome, anexo.tipo, anexo.tamanho)
fim
```

O resultado fornece `cabeçalhos`, `remetente`, `responderPara`,
`destinatários`, `cópia`, `assunto`, `data`, `identificação`, `texto`, `html`,
`anexos`, `conteúdo` e `tamanho`. `responderPara` usa o endereço de `Reply-To`
quando presente e, na ausência dele, o remetente de `From`. Cada anexo contém
`nome`, `tipo`, `dados` e `tamanho`.

Na persistência de uma carta recebida, `remetente` conserva esse autor de
`From`; o valor de `MAIL FROM` é armazenado separadamente como
`remetenteEnvelope`. Essa separação impede que endereços de retorno criados
por transportadores sejam apresentados ao leitor como autores da carta.

O leitor desdobra cabeçalhos, entende palavras UTF-8 codificadas, Base64,
quoted-printable e multipartes aninhadas. Ele limita cabeçalhos, profundidade,
quantidade de partes, anexos individuais e soma dos anexos. Formatos de
caracteres antigos não são convertidos:
uma palavra de cabeçalho que não seja UTF-8 ou ASCII é preservada para que a
aplicação decida como tratá-la. O leitor apenas devolve HTML; não o higieniza
nem o executa.

Antes de aceitar uma submissão ou um `APPEND`, use
`correio.inspecioneCabeçalhos(conteúdo)`. A função devolve uma tabela com
`internacionais` e `cabeçalhos`, ou recusa UTF-8 inválido, `U+FFFD` em
endereços, palavra MIME dentro da parte local e `Message-ID` codificado. Ela
confere integridade estrutural; não substitui SPF, DKIM, DMARC nem a vinculação
do autor à conta autenticada.

Corpo, assunto, nomes de anexos e endereços aceitam UTF-8. Quando remetente
ou destinatário contém Unicode, o cliente exige a extensão SMTPUTF8 e acrescenta
`SMTPUTF8` ao comando `MAIL FROM`. O servidor anuncia e valida essa extensão.
Uma parte local válida recebida entre aspas no caminho SMTP é desaspada e
validada antes da consulta postal; assim, `"josé"` e `josé` alcançam a mesma
caixa, mas escapes inválidos e caracteres perdidos continuam recusados.
Domínios Punycode continuam aceitos: `santafé.dev.br` e
`xn--santaf-gva.dev.br` são normalizados para a mesma identidade nas regras de
`domíniosLocais`.

## Cliente SMTP

```santafé
local cliente = garanta(correio.cliente {
    endereço = "smtp.exemplo.org",
    porta = 587,
    segurança = "inícioTLS",
    nome = "aplicativo.exemplo.org",
    usuário = "rafael",
    senha = so.obterVariável("SENHA_SMTP")
})

garanta(cliente:envieAssíncrono(mensagem,
    função(resultado, falha)
        se falha então
            mostre("entrega recusada:", falha)
        senão
            mostre("aceita:", resultado.identificação)
        fim
        cliente:feche()
        (importe "rede").pareLaço()
    fim))

(importe "rede").laço()
```

`segurança` aceita:

- `"inícioTLS"`: conecta em texto, exige `STARTTLS`, negocia TLS e repete
  `EHLO`; indicado para a porta 587;
- `"TLS"`: TLS desde o primeiro taco; indicado para a porta 465;
- `"nenhuma"`: somente para redes controladas e sem credenciais.

`validarCertificado` é verdadeiro por padrão. Desativá-lo serve apenas para
testes locais. `permitirAutenticaçãoSemTLS` também é falso por padrão.

O tratador recebe `resultado, falha, dado`. Uma resposta SMTP definitiva é
considerada aceita somente depois do código `250` ao fim de `DATA`.

| Opção do cliente | Padrão | Uso |
|---|---:|---|
| `endereço` | `"localhost"` | Endereço DNS ou IP do servidor. |
| `porta` | `587` | Porta SMTP. |
| `segurança` | `"inícioTLS"` | `inícioTLS`, `TLS` ou `nenhuma`. |
| `nome` | `"localhost"` | Nome enviado no `EHLO`. |
| `usuário`, `senha` | ausentes | Credenciais para `AUTH PLAIN`. |
| `validarCertificado` | `verdadeiro` | Valida identidade e cadeia TLS. |
| `tempoLimite` | `10000` | Limite por operação de rede, em ms. |
| `pulso` | ausente | Canal PULSO que recebe o ciclo da entrega. |

`permitirAutenticaçãoSemTLS = verdadeiro` existe apenas para laboratórios
isolados. Não o habilite em redes reais: `AUTH PLAIN` apenas codifica a senha
em Base64 e depende de TLS para sigilo.

### Entrega direta por MX

```santafé
local correio = importe "correio"

garanta(correio.entregueDiretamenteAssíncrono(mensagem, {
    nome = "mail.xn--santaf-gva.dev.br",
    segurança = "oportunista"
}, função(relatório, falha)
    garanta(relatório, falha)
    mostre("entregues:", #relatório.entregues)
    mostre("temporárias:", #relatório.temporárias)
    mostre("permanentes:", #relatório.permanentes)
fim))
```

Destinatários são agrupados por domínio. O cliente consulta MX, respeita a
prioridade e tenta servidores alternativos em falhas temporárias. Se não
existir MX, usa o próprio domínio como MX implícito. Um MX nulo declara que o
domínio não recebe cartas. A opção `oportunista` negocia STARTTLS quando o
destino anuncia suporte, mas permite SMTP em texto quando ele não anuncia;
uma negociação anunciada que falha não sofre rebaixamento silencioso.

O relatório separa `entregues`, `temporárias` e `permanentes`, além de trazer
o diagnóstico por domínio em `domínios`. A fila oficial persiste somente os
temporários para evitar duplicar entregas já aceitas.

### Assinatura DKIM

`correio.dkim.assine(conteúdo, opções)` acrescenta uma assinatura
`rsa-sha256`, usando canonicalização `relaxed/relaxed`. As opções obrigatórias
são `domínio`, `seletor` e `chavePrivada` em PEM. A chave privada deve ser lida
de um arquivo protegido; jamais deve ser incluída no fonte ou no PULSO.

## Servidor SMTP

As portas têm papéis diferentes:

- **25, recebimento entre servidores:** normalmente sem autenticação de
  usuário, aceita apenas `domíniosLocais` e pode oferecer `STARTTLS`;
- **587, submissão:** `STARTTLS`, `exigirAutenticação = verdadeiro` e
  destinatários externos permitidos somente ao usuário autenticado;
- **465, submissão cifrada:** igual à 587, mas com `segurança = "TLS"`.

```santafé
local correio = importe "correio"
local pulso = importe "pulso"
local canalPULSO = garanta(pulso.novo {
    serviço = "correio",
    instância = "smtp-01"
})
canalPULSO:adicioneDestino(
    garanta(pulso.registrador("/var/log/santafé/correio.pulso"))
)

local servidor = garanta(correio.servidor {
    endereço = "0.0.0.0",
    porta = 587,
    nome = "smtp.exemplo.org",
    segurança = "inícioTLS",
    certificado = "/etc/letsencrypt/live/exemplo/fullchain.pem",
    chavePrivada = "/etc/letsencrypt/live/exemplo/privkey.pem",
    exigirAutenticação = verdadeiro,
    domíniosLocais = { "exemplo.org" },

    autentique = função(usuário, senha, conclua)
        -- Pode iniciar segredo.confiraSenhaAssíncrono e chamar conclua.
        conclua(usuário == "teste" e senha == "somente-no-exemplo")
    fim,

    autorizeRemetente = função(identidade, remetente, conclua)
        -- Vincule MAIL FROM à caixa devolvida por autentique.
        conclua(remetente == identidade.caixa.endereço)
    fim,

    receba = função(mensagem, conclua)
        -- Confirme apenas depois de persistir.
        minhaFila:receba(mensagem, conclua)
    fim,

    pulso = canalPULSO
})

garanta(servidor:escute())
```

`autentique`, `autorizeRemetente`, `autorize` e `receba` podem devolver
imediatamente um valor ou concluir depois pela função recebida. Para recusar
de forma síncrona, devolva `falso, motivo`; devolver `nulo` significa que a
conclusão será assíncrona. Quando `autentique` devolve uma tabela, o servidor
a conserva como `identidade` da sessão e a entrega aos demais tratadores.

`receba` obtém uma tabela com `remetente`, `destinatários`, `conteúdo`,
`tamanho`, `endereçoRemoto`, `usuário`, `identidade`, `smtpUTF8` e
`recebidaEm`.

O servidor aceita tanto `AUTH PLAIN <resposta>` quanto o desafio em duas
etapas (`AUTH PLAIN`, resposta `334`, credencial Base64). Ele rejeita novo
`AUTH` depois do sucesso e também durante uma transação iniciada por
`MAIL FROM`, conforme o contrato SMTP AUTH. A credencial nunca deve ser
registrada no PULSO.

Sem `autorize`, uma sessão não autenticada só pode enviar para os
`domíniosLocais`. Isso impede que o servidor nasça como encaminhador aberto.

### Opções do servidor

| Opção | Padrão | Uso |
|---|---:|---|
| `endereço` | `"0.0.0.0"` | Interface de escuta. |
| `porta` | `2525` | Porta de escuta. |
| `nome` | `"localhost"` | Nome anunciado na saudação e no `EHLO`. |
| `segurança` | `"nenhuma"` | `nenhuma`, `inícioTLS` ou `TLS`. |
| `certificado`, `chavePrivada` | exigidos com TLS | Caminhos PEM. |
| `tempoLimite` | `60000` | Limite de inatividade por operação, em ms. |
| `limiteMensagem` | `50 MiB` | Corpo SMTP bruto máximo recebido. |
| `limiteLinha` | `998` | Tacos máximos por linha SMTP. |
| `limiteComandos` | `100` | Comandos aceitos na sessão. |
| `limiteDestinatários` | `100` | Destinatários por mensagem. |
| `limiteConexões` | `1000` | Sessões simultâneas globais. |
| `limiteConexõesPorEndereço` | `20` | Sessões simultâneas por IP. |
| `limiteNovasConexõesPorMinuto` | `60` | Ritmo de aceitação por IP. |
| `limiteTentativasDeAutenticação` | `3` | Falhas de autenticação por sessão. |
| `exigirAutenticação` | `falso` | Exige login antes do envelope. |
| `domíniosLocais` | `{}` | Domínios recebidos sem retransmissão. |
| `autentique` | — | Confere a credencial e pode devolver uma identidade. |
| `autorizeRemetente` | — | Autoriza o `MAIL FROM` para a identidade autenticada. |
| `autorize` | — | Autoriza cada destinatário do envelope. |
| `receba` | obrigatório | Persiste ou enfileira antes da resposta SMTP 250. |
| `pulso` | ausente | Canal de telemetria. |

`servidor:inicie()` arma o aceite sem entrar no laço. `servidor:escute()`
inicia e permanece em `rede.laço()`. `estatísticas()` devolve conexões,
aceites, recusas, mensagens, autenticações e a fotografia `vigia` da
proteção de conexões. `feche()` encerra as sessões e, nesta versão, também
solicita a parada do laço compartilhado.

Os três limites de conexão são aplicados pela biblioteca `vigia`, incorporada
ao servidor SMTP. Não há um segundo serviço nem dependência do Forte: o
Correio conserva a política SMTP e o Vigia fornece o mecanismo local de
contagem, concorrência, limpeza limitada de memória e acontecimentos PULSO.

## Fila MariaDB

```santafé
local Depósito = importe "correio.depósito"
local objetos = garanta(Depósito.novo {
    raiz = "/var/lib/santafé/correio",
    limite = 50 * 1024 * 1024
})

objetos:prepareAssíncrono(função(preparou, falha)
    garanta(preparou, falha)
fim)

local fila = garanta(correio.filaMariaDB(piscina, {
    tabela = "correio_fila",
    tempoDaReserva = 300,
    depósito = objetos
}))

fila:crieEstruturaAssíncrona(função(criou, falha)
    garanta(criou, falha)
fim)
```

Entradas recebidas usam `fila:receba(mensagem, conclua)`. Saídas usam:

1. `adicioneAssíncrono(mensagem, tratador)`;
2. `reservePróximaAssíncrono(tratador)`;
3. envie a reserva pelo cliente SMTP;
4. `marqueEntregueAssíncrono(id, tratador)` ou
   `adieAssíncrono(id, falha, segundos, tratador)`;
5. na inicialização, chame
   `recupereReservasExpiradasAssíncrono(tratador)`.

A reserva usa um bilhete aleatório único e `UPDATE ... ORDER BY ... LIMIT 1`,
evitando que dois trabalhadores recebam a mesma linha. O prazo permite
recuperar uma mensagem quando um processo morre durante a entrega.

Para concluir uma falha e criar seu aviso na mesma transação, use
`marqueFalhouEAviseAssíncrono(id, falha, destinatários, detalhes, tratador)`.
`soliciteAvisoAssíncrono` registra o aviso único de atraso. Os avisos são
reservados por `reservePróximoAvisoAssíncrono`; o adaptador MariaDB do CD os
entrega localmente de maneira idempotente.

Itens estruturalmente inválidos acumulam `falhasInternas` e deixam de girar
indefinidamente na fila. `listeQuarentenaAssíncrono` permite inspecioná-los e
`reprocesseQuarentenaAssíncrono` os libera depois da correção da causa. Uma
recusa SMTP comum, temporária ou definitiva, nunca é confundida com
quarentena operacional.

Com `depósito`, o MIME é gravado de forma atômica e durável antes do
`INSERT`; a fila guarda somente seu resumo e tamanho. Registros antigos com
`LONGBLOB` continuam legíveis. O método avançado
`adicioneFormadaAssíncrono(mensagem, conteúdo, objeto, tratador [, dado])` é
destinado ao adaptador do CD: ele reutiliza um MIME e um objeto já persistidos,
garantindo que a fila e a cópia em Enviadas sejam idênticas taco por taco.
Aplicativos comuns devem preferir `adicioneAssíncrono`.

`filaMemória` existe para testes e desenvolvimento. Ela não é durável e não
deve confirmar correio importante em produção.

## PULSO

Passe um canal em `pulso` ao cliente ou servidor. O Correio emite, entre
outros:

- `correio.servidorIniciado` e `correio.servidorEncerrado`;
- `correio.conexãoAceita`, `correio.conexãoLimitada` e
  `correio.conexãoFechada`;
- `correio.autenticado` e `correio.autenticaçãoRecusada`;
- `correio.mensagemRecebida`, `correio.conteúdoMalformadoRecusado` e
  `correio.persistênciaFalhou`;
- `correio.triagem` e `correio.triagemIndisponível`;
- `correio.entregaIniciada`, `correio.entregue` e
  `correio.entregaFalhou`.
- `correio.avisoDeEntregaCriado` e `correio.avisoDeEntregaFalhou`.
- `correio.imapIniciado`, `correio.imapConexãoAceita`,
  `correio.imapAutenticado`, `correio.imapUnicodeAtivado`,
  `correio.imapUnicodeCompatibilidade`, `correio.imapCartaAnexada`,
  `correio.imapCartasCopiadas` e as recusas correspondentes.

Senhas, credenciais `AUTH`, corpo e anexos nunca são enviados ao PULSO.

## Limites desta versão

- `AUTH PLAIN` é o mecanismo inicial; ele é seguro somente dentro de TLS;
- SPF e DMARC precisam ser publicados no DNS; o programa não pode criá-los
  sozinho;
- os avisos DSN cobrem as cartas originadas nas caixas locais e a Agência
  conserva o caminho reverso vazio dos avisos automáticos;
- o IMAP anuncia `UTF8=ACCEPT`, aceita `ENABLE UTF8=ACCEPT` sem exigi-lo de
  clientes IMAP comuns e oferece leitura integral ou parcial, pesquisa,
  sinalizadores,
  movimentação, a pasta Arquivadas com `\\Archive`, `IDLE`, `APPEND` em
  Rascunhos/Enviadas, marcação de leitura compartilhada com o Carteiro e
  `UIDPLUS`, incluindo `COPY`, `UID COPY` e a resposta `COPYUID`; ainda não
  oferece pastas criadas pelo usuário; o expurgo fora da
  Lixeira conserva a carta nela, enquanto `EXPUNGE`, `UID EXPUNGE` e `CLOSE`
  dentro da Lixeira removem definitivamente a referência e liberam a cota;
  `\Deleted` persiste no MariaDB entre conexões e é limpo ao mover a carta;
- `feche()` encerra o laço `rede` compartilhado. Ao hospedar mais de um
  serviço no mesmo processo, coordene o encerramento no processo principal.

Para receber correio real da Internet, além do programa são necessários DNS
MX, PTR reverso, certificados, fila durável, políticas de abuso, observação,
cópias de segurança e configuração de reputação.
