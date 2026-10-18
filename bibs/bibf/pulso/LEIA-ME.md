# PULSO/1

**PULSO** significa **Protocolo Unificado de Leituras, Sinais e Operações**.
Ele foi concebido pela Santafé como uma base comum para serviços emitirem
telemetria, eventos operacionais e, futuramente, receberem operações do
Forte de maneira autenticada, limitada e auditável.

PULSO/1 já é funcional sem o Forte: um serviço produz envelopes
estruturados e os entrega a registradores locais, memória de testes ou
terminal. O futuro transporte remoto será outro destino do mesmo canal.

## Princípios

- **Confiável:** mensagens identificadas, sequenciadas, limitadas e
  validadas antes da entrega.
- **Intuitivo:** uma API pequena, com leituras, sinais e operações.
- **Funcional:** registro local e enquadramento binário fazem parte da
  primeira versão; não são apenas uma proposta futura.
- **Independente:** o serviço continua operando se um destino falhar ou se o
  Forte ainda não existir.
- **Seguro por construção:** campos sigilosos conhecidos são protegidos e
  o formato rejeita ciclos, tipos não serializáveis e mensagens sem limite.

## Envelope

Toda mensagem PULSO/1 possui:

| Campo | Significado |
|---|---|
| `protocolo` | Sempre `"PULSO"`. |
| `versão` | Versão principal do contrato; nesta especificação, `1`. |
| `tipo` | `leitura`, `sinal`, `operação`, `confirmação`, `recusa` ou `pulsoDeVida`. |
| `nome` | Nome estável e legível do evento. |
| `identificação` | Identificador único da mensagem. |
| `origem` | Serviço e instância, como `correio/smtp-01`. |
| `sequência` | Contador crescente dentro da origem. |
| `carimboDeHora` | Segundos desde a época Unix. |
| `validade` | Quantos segundos a mensagem pode orientar uma decisão. |
| `prioridade` | `baixa`, `normal`, `alta` ou `crítica`. |
| `correlação` | Identificação da operação respondida, quando aplicável. |
| `dados` | Tabela com o conteúdo específico do evento. |

Exemplo:

```santafé
{
    protocolo = "PULSO",
    versão = 1,
    tipo = "sinal",
    nome = "autenticaçãoRecusada",
    identificação = "6a123456-a1b2c3d4-e5f60718-00000001",
    origem = "correio/smtp-01",
    sequência = 1,
    carimboDeHora = 1787724000,
    validade = 30,
    prioridade = "alta",
    dados = {
        endereço = "192.0.2.10",
        usuário = "ana"
    }
}
```

## Tipos

### Leitura

Uma medida observada: profundidade de fila, conexões, latência, quantidade
de falhas ou uso de recursos. Leituras não ordenam mudanças.

### Sinal

Um acontecimento: serviço iniciado, entrega recusada, limite alcançado ou
comportamento anormal. Sinais podem gerar alertas e investigações.

### Operação

Uma solicitação explícita de mudança. Na futura integração com o Forte,
operações exigirão um canal autenticado, autorização por capacidade,
validade curta e comportamento idempotente.

### Confirmação e recusa

Respondem a uma operação por meio de `correlação`. Confirmar significa
que a operação foi aplicada; receber a mensagem não basta. Uma recusa deve
informar uma razão segura e não revelar segredos.

### Pulso de vida

Informa que a origem está ativa e resume seu estado. A ausência de pulsos
pode indicar falha, mas nunca deve, isoladamente, autorizar uma mitigação
destrutiva.

## Uso local

```santafé
local pulso = importe "pulso"

local canal = garanta(pulso.novo({
    serviço = "correio",
    instância = "smtp-01"
}))

canal:adicioneDestino(
    garanta(pulso.registrador("/var/log/santafé/correio.pulso"))
)

canal:sinal("serviçoIniciado", {
    endereço = "0.0.0.0",
    porta = 25
})

canal:leitura("filaDeSaída", {
    pendentes = 18,
    adiadas = 3
})

canal:feche()
```

O registrador grava um objeto JSON UTF-8 por linha. Ele aceita
`limiteArquivo` e gira o arquivo antes de ultrapassar esse limite.

### Opções do canal

| Opção | Padrão | Função |
|---|---:|---|
| `serviço` | obrigatória | Nome estável do produtor. |
| `instância` | `"principal"` | Distingue processos do mesmo serviço. |
| `limiteFila` | `1024` | Quantidade máxima de mensagens aguardando entrega. |
| `limiteDados` | `65536` | Tamanho máximo do campo `dados`, em tacos de JSON. |
| `limiteProfundidade` | `12` | Profundidade máxima das tabelas em `dados`. |
| `limiteItens` | `2048` | Quantidade máxima de campos e itens visitados. |
| `camposSigilosos` | `{}` | Nomes adicionais que devem virar `[protegido]`. |

### Métodos do canal

- `adicioneDestino(destino)` e `removaDestino(destino)` controlam os
  consumidores;
- `leitura`, `sinal` e `operação` criam os três tipos principais;
- `confirmação` e `recusa` exigem a identificação correlacionada;
- `pulsoDeVida(dados)` informa que a origem continua ativa;
- `estatísticas()` devolve emitidas, entregues, recusadas, falhas, pendentes
  e quantidade de destinos;
- `feche()` despeja a fila e fecha cada destino.

Um destino é uma tabela com `envie(este, mensagem)`. Ele pode fornecer
`esvazie()` e `feche()`. A entrega local é síncrona e limitada: um destino
lento pode atrasar o produtor, portanto o registrador em arquivo deve ser
usado com limites e armazenamento local previsível. O futuro destino remoto
terá sua própria fila durável e contrapressão.

O registrador de PULSO/1 usa atualmente `es` para acrescentar JSON por linha.
Essa escrita é bloqueante e foi concebida para telemetria local de volume
moderado. A evolução prevista é acrescentar uma operação assíncrona
enfileirada à biblioteca `arquivo`; a gravação durável que ela oferece hoje
substitui um objeto inteiro e não é apropriada para acrescentar continuamente
a um registro JSONL.

## Perfil binário PULSO/1

O enquadramento de rede é independente de TCP, TLS ou outro transporte
confiável. Cada quadro contém:

```text
+-------------------------+----------------------------------+
| tamanho: 4 tacos        | envelope JSON UTF-8              |
| inteiro sem sinal, rede | exatamente "tamanho" tacos      |
+-------------------------+----------------------------------+
```

O tamanho usa ordem de rede, do taco mais significativo para o menos
significativo. O limite padrão é 1 MiB por mensagem. Um receptor deve
rejeitar um tamanho inválido antes de reservar ou acumular o corpo.

```santafé
local quadro = garanta(pulso.codifique(mensagem))
local decodificador = garanta(pulso.novoDecodificador {
    limiteMensagem = 1024 * 1024,
    limiteLote = 4 * 1024 * 1024
})
local mensagens = garanta(decodificador:alimente(quadro))
```

O decodificador aceita quadros fragmentados e vários quadros em sequência.
`limiteMensagem` vale para cada envelope; `limiteLote` limita a memória
acumulada quando chegam vários quadros ou fragmentos. Depois de uma entrada
inválida, chame `reinicie()` antes de reutilizá-lo. `pendente()` informa
quantos tacos ainda aguardam um quadro completo.

## Entrega e repetição

Destinos locais recebem cada mensagem uma vez por tentativa. O futuro
transporte remoto usará entrega **pelo menos uma vez**: uma confirmação
perdida pode provocar reenvio. Consumidores devem guardar
`identificação`, ignorar duplicatas e tratar operações como idempotentes.

A ordem só é definida dentro da mesma `origem` e pode ser verificada por
`sequência`. Mensagens de origens diferentes não possuem ordem global.

## Dados sigilosos

PULSO não é um depurador de conteúdo. Serviços não devem emitir:

- senhas ou comandos SMTP `AUTH`;
- bilhetes de sessão;
- chaves privadas;
- corpo ou anexos de correio;
- dados pessoais sem necessidade operacional.

O núcleo substitui campos sigilosos conhecidos por `[protegido]`, inclusive
em tabelas internas. Essa proteção é uma segunda barreira e não substitui a
escolha correta dos dados na origem.

## Futuro transporte do Forte

O destino remoto deverá acrescentar, sem mudar os produtores atuais:

- TLS mútuo;
- autenticação e autorização por capacidade;
- confirmações, reenvio e armazenamento temporário;
- proteção contra repetição;
- negociação de versão;
- contrapressão e filas limitadas;
- registro de operações e de seus resultados.

O Correio e o Caminheiro são os primeiros produtores reais do PULSO. Ambos
recebem um canal em `pulso`: o Correio registra o ciclo SMTP e o Caminheiro
registra conexões, requisições, respostas e falhas de tratamento. Nenhum dos
dois envia corpo, credencial, biscoito ou cabeçalho de autorização.

O Forte ainda não é necessário para esse uso. Quando existir, será ligado
como outro destino do canal, sem mudar os produtores nem tornar o Correio e o
Caminheiro dependentes dele.

Na arquitetura futura, o Vigia continuará sendo o braço independente de
proteção local de cada serviço. Os sentinelas existirão somente dentro do
Forte: serão seus operários especializados, acompanhando os acontecimentos
PULSO de cada serviço ou domínio e trabalhando de forma coordenada. Portanto,
`sentinela` não será nome de objeto nem conceito público do Vigia.
