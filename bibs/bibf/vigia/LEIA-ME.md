# Vigia

O **Vigia** é a biblioteca Santafé de proteção local na camada de
aplicação. Ele é incorporado ao serviço protegido, conserva seu estado em
memória e continua aplicando limites mesmo quando PULSO, Forte ou qualquer
observador externo estiver indisponível.

O Vigia fornece o mecanismo comum. A política continua pertencendo ao
serviço: o Correio sabe o que é uma conexão SMTP, o Caminheiro conhece uma
rota HTTP, Nomes conhece uma consulta DNS e o Carteiro conhece uma operação
de usuário.

O termo **sentinela** não faz parte do Vigia. Ele está reservado aos futuros
operários especializados do Forte.

## Primeiro uso

```santafé
local Vigia = importe "vigia"

local proteção = garanta(Vigia.novo({
    nome = "meu-serviço.entrada",
    janela = 60,
    limiteNaJanela = 30,
    limiteSimultâneo = 5,
    limiteGlobal = 200
}))

local admitida, decisão = proteção:admita(endereço)
se não admitida então
    mostre("recusado:", decisão.motivo)
    retorne
fim

-- Execute o trabalho protegido.

garanta(proteção:conclua(endereço))
```

Cada admissão aceita deve ter uma chamada correspondente a `conclua`. Uma
tentativa recusada não deve ser concluída.

## `Vigia.novo(opções)`

Cria uma proteção independente.

| Opção | Padrão | Função |
| --- | ---: | --- |
| `nome` | `"vigia"` | Identifica a proteção nas estatísticas e no PULSO. |
| `janela` | `60` | Duração da janela de admissões, em segundos. |
| `limiteNaJanela` | `60` | Tentativas permitidas por chave; zero desativa esse limite. |
| `limiteSimultâneo` | `20` | Admissões ativas por chave; zero desativa esse limite. |
| `limiteGlobal` | `1000` | Admissões ativas na instância; zero desativa esse limite. |
| `duraçãoDoBloqueio` | `0` | Bloqueio automático após excesso; zero apenas recusa a tentativa. |
| `limiteDeFalhas` | `0` | Falhas permitidas na janela; zero não bloqueia por falhas. |
| `janelaDeFalhas` | valor de `janela` | Janela independente para falhas. |
| `bloqueioPorFalhas` | `300` | Duração do bloqueio provocado por falhas. |
| `máximoDeChaves` | `10000` | Limite rígido de chaves conservadas em memória. |
| `ociosidade` | duas janelas | Prazo para remover uma chave inativa. |
| `pulso` | ausente | Canal PULSO opcional. |
| `relógio` | `so.tempo` | Fonte de tempo substituível para ensaios determinísticos. |

Os limites valem para cada instância e processo. Uma implantação com vários
processos continua protegida localmente, mas a visão agregada caberá ao futuro
Forte.

## Métodos

### `proteção:admita(chave [, peso])`

Registra uma tentativa e verifica bloqueio, concorrência, limite global e
frequência. Retorna `verdadeiro, decisão` quando aceita e
`falso, decisão` quando recusada. Uma tentativa recusada também conta na
janela para impedir que o limite seja contornado.

`decisão.motivo` pode ser `"bloqueio"`, `"limite global"`,
`"limite simultâneo"`, `"limite da janela"` ou `"capacidade"`.

### `proteção:conclua(chave [, peso])`

Encerra admissões aceitas e reduz os contadores simultâneos. Recusa uma
conclusão sem admissão correspondente, pois isso indicaria erro no ciclo de
vida do serviço.

### `proteção:registreFalha(chave [, peso])`

Acrescenta falhas na janela independente. Quando `limiteDeFalhas` for maior
que zero, alcançar o limite aplica um bloqueio por `bloqueioPorFalhas`
segundos. Serve, por exemplo, para autenticações malsucedidas.

### `proteção:bloqueie(chave [, duração [, motivo]])`

Aplica um bloqueio local explícito. A duração omitida usa
`bloqueioPorFalhas`. Um novo prazo somente prolonga um bloqueio existente;
nunca o encurta.

### `proteção:libere(chave)`

Retira um bloqueio explícito ou automático e zera as falhas acumuladas.
Retorna `falso` quando a chave não estiver bloqueada.

### `proteção:estado(chave)`

Devolve uma fotografia sem expor as tabelas internas: admissões ativas,
total global, ocorrências na janela, falhas e prazo do bloqueio. Devolve
`nulo` para uma chave desconhecida.

### `proteção:limpe()`

Remove imediatamente chaves inativas cujo prazo de ociosidade terminou e
devolve a quantidade removida. A mesma limpeza ocorre automaticamente a cada
256 operações.

### `proteção:estatísticas()`

Devolve contadores acumulados de admissões, recusas, conclusões, falhas,
bloqueios, liberações, remoções, recusas por capacidade e falhas do destino
PULSO.

## Acontecimentos PULSO

Quando recebe um canal em `pulso`, o Vigia pode emitir:

- `vigia.limiteAtingido`;
- `vigia.capacidadeAtingida`;
- `vigia.bloqueioAplicado`;
- `vigia.bloqueioRetirado`.

Falha no canal PULSO não libera uma operação nem interrompe a proteção
local. O contador `falhasDoPulso` permite diagnosticar essa condição.

## Limites da proteção

O Vigia protege a camada de aplicação. Ele não substitui firewall, nftables,
XDP, proteção do enlace ou BGP/RTBH. Se o tráfego já saturou a interface,
a aplicação não possui capacidade para resolver o incidente sozinha.
