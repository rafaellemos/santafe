# Nomes: DNS em Santafé

`nomes` implementa o protocolo DNS em arquivos `.fé`. Ela não usa
libknot, BIND, Unbound nem outra implementação de DNS. A biblioteca C `rede`
fornece somente UDP, TCP e o laço assíncrono.

## Camadas

- `nomes`: mensagens, nomes comprimidos e registros de recurso;
- `nomes.zona`: zonas estáticas, curingas, CNAME, NODATA e NXDOMAIN;
- `nomes.autoridade`: servidor UDP/TCP que responde apenas pelas suas zonas;
- `nomes.resolvedor`: resolução iterativa desde a raiz, memrap por TTL e ACL;
- `nomes.dnssec`: assinatura e registros DNSSEC;
- `nomes.acesso`: prefixos IPv4/IPv6 e limite de taxa por origem.

São interpretados `A`, `AAAA`, `NS`, `CNAME`, `SOA`, `PTR`, `MX`, `TXT`,
`SRV`, `CAA` e `OPT`. Os tipos `DS`, `RRSIG`, `NSEC`, `DNSKEY`, `NSEC3`,
`TLSA`, `SVCB` e `HTTPS` são reconhecidos e preservados como dados crus, assim
como qualquer tipo numérico desconhecido. `QUALQUER` representa a consulta
DNS de tipo 255.

## Mensagens

```santafé
local nomes = importe "nomes"

local pacote = garanta(nomes.novaConsulta(
    "xn--santaf-gva.dev.br", "MX", 1200, verdadeiro
))
local mensagem = garanta(nomes.decodifiqueMensagem(pacote))
mostre(mensagem.identificação, mensagem.perguntas[1].nomeDoTipo)

-- saída: 1200    MX
```

Os nomes recebidos e devolvidos pelo protocolo terminam em ponto. Domínios
Unicode devem ser convertidos antes com `rede.domínioASCII`; a apresentação
ao usuário pode usar `rede.domínioUnicode`.

## Zona autoritativa

```santafé
local zona = importe "nomes.zona"

local minhaZona = garanta(zona.nova({
    nome = "exemplo.org",
    ttlPadrão = 3600,
    registros = {
        { nome = "@", tipo = "SOA", dados = {
            mestre = "ns1", responsável = "dns", série = 2026082701,
            atualização = 3600, novaTentativa = 900,
            expiração = 1209600, mínimo = 300 } },
        { nome = "@", tipo = "NS", dados = "ns1" },
        { nome = "ns1", tipo = "A", dados = "192.0.2.53" },
        { nome = "www", tipo = "A", dados = "192.0.2.10" },
        { nome = "@", tipo = "MX",
            dados = { preferência = 10, troca = "correio" } },
        { nome = "correio", tipo = "A", dados = "192.0.2.25" }
    }
}))
```

`@` representa o ápice. Nomes sem ponto final são relativos à zona; nomes
com ponto final são absolutos. Toda zona precisa de `SOA` e ao menos um `NS` no
ápice.

Um `NS` abaixo do ápice cria um corte de delegação. Consultas no corte ou
abaixo dele recebem uma referência sem a marca autoritativa, acompanhada apenas
da cola `A`/`AAAA` disponível. Nós vazios são distinguidos de nomes inexistentes,
e curingas obedecem ao ancestral existente mais próximo.

```santafé
local servidor = garanta((importe "nomes.autoridade").novo({
    endereço = "192.0.2.53", porta = 53, zonas = { minhaZona }
}))
garanta(servidor:escute())
```

O autoritativo aceita DNS por UDP e TCP, limita a taxa por origem e respeita o
tamanho UDP anunciado por EDNS. Se a resposta não couber, marca `truncada` e o
cliente pode repeti-la por TCP.

## Resolvedor recursivo

```santafé
local resolvedor = garanta((importe "nomes.resolvedor").novo({
    endereço = "127.0.0.1",
    porta = 53,
    prefixosPermitidos = {
        "127.0.0.0/8", "::1/128", "143.208.252.0/22"
    }
}))
garanta(resolvedor:escute())
```

O resolvedor não é um encaminhador: consulta os servidores-raiz, acompanha
delegações e resolve servidores sem cola quando necessário. Confere o
identificador, a origem, a porta e a pergunta de cada resposta. Respostas
positivas e negativas permanecem na memrap apenas durante o TTL. Referências
fora do caminho consultado, conjuntos `NS` de origens misturadas, respostas de
outro nome e cadeias `CNAME` cíclicas ou conflitantes são rejeitados.

Sem `prefixosPermitidos`, somente `127.0.0.0/8` e `::1/128` são atendidos.
Origens externas são descartadas silenciosamente. Para a rede do ASN 265132,
adicione explicitamente `143.208.252.0/22`.

Essa ACL evita transformar o serviço num resolvedor aberto, mas deve ser
acompanhada de filtragem antisspoofing BCP 38/uRPF nos roteadores. A biblioteca
também limita taxa, explosão, consultas pendentes, saltos e tamanho das
respostas, conexões TCP e filas de saída; essas proteções não substituem a
filtragem de origem da rede.

## DNSSEC e limite deliberado da primeira versão

O autoritativo assina zonas marcadas com `dnssec = verdadeiro`. Ele publica
`DNSKEY`, `RRSIG` e `NSEC`, calcula o `DS` SHA-256 e assina tanto respostas
positivas quanto a negação de existência. A chave RSA precisa ter pelo menos
2048 ticos. Como a assinatura é produzida ao carregar a zona, a operação deve
reiniciar o serviço periodicamente antes do vencimento das RRSIG; a unidade
fornecida faz essa renovação diariamente.

O resolvedor ainda **não valida DNSSEC**. Ele entende respostas que carregam
tipos desconhecidos, mas nunca afirma que os dados foram autenticados. Use-o
em laboratório e em rede controlada; a validação DNSSEC, testes de carga e
operação redundante são requisitos antes de classificá-lo como resolvedor
recursivo de produção para uma rede inteira.

Transferências AXFR/IXFR, NOTIFY, atualização dinâmica e validação DNSSEC no
resolvedor permanecem etapas posteriores.
