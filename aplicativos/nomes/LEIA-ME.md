# Serviços de Nomes Santafé

Os dois processos são separados por segurança e por função:

- `autoridade.fé`: responde publicamente pelas zonas administradas;
- `resolvedor.fé`: busca respostas para clientes de prefixos permitidos.

Nunca publique o resolvedor sem ACL. No exemplo, a autoridade ocupa
`143.208.252.1:53`, enquanto o resolvedor ocupa `127.0.0.1:53`. Se o resolvedor
também precisar atender assinantes, use um endereço interno distinto e mantenha
`NOMES_RESOLVEDOR_PREFIXOS` limitado aos blocos da rede.

## Arquivos

- `zonas.exemplo.fé`: zona direta e reversa de exemplo;
- `operação/nomes.env.exemplo`: ambientes dos dois processos;
- `operação/nomes-autoridade.service`: unidade da autoridade;
- `operação/nomes-autoridade.service.d/dnssec.conf`: renovação diária das
  assinaturas por recarga integral e segura da zona;
- `operação/nomes-resolvedor.service`: unidade do resolvedor.

As zonas marcadas com `dnssec = verdadeiro` são assinadas ao iniciar a
autoridade. As assinaturas padrão valem quinze dias. A unidade limita cada
execução a um dia e, combinada com `Restart=always`, recarrega e assina a zona
novamente todos os dias. Os dois autoritativos devem iniciar em horários
distintos para não renovarem simultaneamente.

O bloco `143.208.252.0/22` contém quatro zonas reversas `/24`. A primeira,
correspondente a `143.208.252.0/24`, é
`252.208.143.in-addr.arpa.`. O endereço `143.208.252.1` corresponde ao registro:

```text
1 IN PTR xn--santaf-gva.dev.br.
```

Delegar a zona reversa no Registro.br continua exigindo ao menos dois
servidores autoritativos reais. Duas unidades na mesma máquina não constituem
redundância.

O titular do bloco é a Telemulti. Por isso a autoridade reversa usa os nomes
institucionais `sn1.telemulti.net.br` e `sn2.telemulti.net.br`. A sigla `sn`
significa “servidor de nomes”. A zona continua
se chamando `252.208.143.in-addr.arpa.` e cada PTR representa o serviço
efetivamente associado ao respectivo IP.

Antes de delegar a zona, publique e valide os endereços dos servidores:

```text
sn1.telemulti.net.br. A 143.208.252.1
sn2.telemulti.net.br. A 143.208.252.3
```

`252-208-143.telemulti.net.br` pode ser usado como rótulo humano ou página de
inventário do bloco, mas não substitui os nomes distintos dos dois servidores.
Quando apenas os registros NS e SOA mudam, a chave DNSSEC pode ser conservada e
o DS do pai permanece igual. O DS só muda quando a chave DNSKEY muda.

## Verificação

```sh
dig @143.208.252.1 xn--santaf-gva.dev.br SOA +norecurse
dig @143.208.252.1 -x 143.208.252.1 +norecurse
dig @127.0.0.1 example.com A
dig @127.0.0.1 example.com A +tcp
dig @1.1.1.1 xn--santaf-gva.dev.br DNSKEY +dnssec
dig @1.1.1.1 -x 143.208.252.1 +dnssec
```

## Descoberta dos serviços postais

A zona postal publica os serviços cifrados e de submissão para que clientes
compatíveis não precisem adivinhar portas ou modos de segurança:

```text
_imaps._tcp       SRV 0 1 993 xn--santaf-gva.dev.br.
_submissions._tcp SRV 0 1 465 xn--santaf-gva.dev.br.
_submission._tcp  SRV 0 1 587 xn--santaf-gva.dev.br.
```

`_imaps` e `_submissions` iniciam TLS desde o primeiro taco. `_submission`
usa STARTTLS obrigatório. Em zonas protegidas, cada conjunto SRV também deve
ser acompanhado por sua assinatura RRSIG.

O teste opcional `testes/integracao/teste_nomes_internet.fé` percorre a
hierarquia pública a partir dos servidores-raiz. Ele não integra `make testar`,
porque algumas redes bloqueiam DNS direto para a Internet.

Antes da publicação, valide UDP e TCP 53 no firewall, a delegação direta, a
delegação reversa e a independência do segundo autoritativo.
