# Santafé dados.14 — validação operacional conjunta

Não instalar em produção. Candidato pronto para homologação, sem aprovação
para promoção estável. Confira `SHA256SUMS`, `ESTADO.json` e `RELATORIO.md`.

A base é o arquivo imutável dados.13 indicado em `preparar.py`. O núcleo,
as bibliotecas migradas, ONFÉ, SLS e as gramáticas mantêm o comportamento da
base. A revisão reúne o ensaio operacional e a correção de upload já validada
separadamente. SLS: 1.0.0-dados.14; IBA: santafe-3; kits experimentais: 0.0.14.

`conjunto.py` exige a captura privada previamente autorizada e a réplica
encerrada. Reutiliza os bancos/depósitos de ensaio, verifica exclusividade e
trabalha em namespaces próprios. Não execute o roteiro contra caminhos de
produção. Os arquivos privados e credenciais não fazem parte desta entrega.

Integrações reais do laboratório: MariaDB, nginx, DNS/DNSSEC Santafé, SMTP,
IMAP, autenticação postal, ClamAV, Certbot e Pebble. O retransmissor é local,
a CA é privada e não existe rota de saída. A interface dummy existe somente
para permitir resolução GIO/AI_ADDRCONFIG no namespace sem acesso externo.
Nenhuma política AppArmor é modificada. O teste usa a base daily do ClamAV
mais uma assinatura sintética EICAR; não representa todas as bases de produção.

Carga concluída: 3600,42 segundos, seis leitores dos dois Carteiros, 43.176
pedidos HTTP; 95% em até 53,64 ms. SMTP, IMAP, filas e upload foram testados
fora da carga. A renovação ACME ocorreu durante a carga. Consumidores postais
reiniciados só na réplica carregaram o certificado novo. A reversão preservou
mensagens, anexos e imagens; a leitura HTTPS das imagens foi conferida em um
ensaio complementar. A carga não representa capacidade máxima.

O único envio externo foi o complemento dados.13 pelo Mailjet, recebido com
acentos corretos segundo o usuário. Dados.14 não enviou mensagens externas.
Emissão pública ACME permanece sem homologação, por ausência de subdomínio
exclusivo. Não há comando de instalação ou publicação neste candidato.

Para conferir esta entrega, entre no diretório extraído e execute:

```sh
sha256sum -c SHA256SUMS
```

Isso verifica os arquivos sem executar o candidato ou alterar serviços.
