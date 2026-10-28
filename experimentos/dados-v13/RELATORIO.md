# Dados.13 — integrações e correção do upload

Pronto para homologação; ainda não aprovado para promoção estável.
Base imutável: dados.12, fontes SHA-256
`1de126f3f0f16dbf21079f39b7f8847b03250178093c446e4e4ba25f0a2ab4e8`.
IBA `santafe-3`; SLS `1.0.0-dados.13`; editores experimentais `0.0.13`.
Listas, nulo armazenável, ONFÉ e delimitadores `[=[...]=]`/`[==[...]==]`
mantêm seu contrato. Não há nova funcionalidade da linguagem.

## Defeito identificado e corrigido

O portal aceitava um PNG truncado de 25 bytes porque conferia apenas assinatura
e dimensões. A reprodução registrou a gravação desse arquivo. A correção
`estrutura-upload.fé`, aplicada pela transformação `aplicar-portal.py`, verifica
limites e CRC dos blocos PNG, ordem essencial e IEND final; para JPEG, verifica
segmentos, quadro, varredura e EOI final. Rejeita truncamento e dados excedentes.
É uma verificação estrutural, não um decodificador de pixels: não comprova a
validade de toda a imagem comprimida. Os limites de tamanho/dimensões existentes
permanecem necessários. Não houve alteração do limite para fazer testes passarem.

O ensaio específico passou no macOS e Debian: PNG gerado de 92 bytes, todos os
92 prefixos truncados e mutações de um bit desde o nono byte, JPEG real, sete
truncamentos JPEG, dados excedentes e formato não aceito. O ensaio HTTP também
conferiu PNG/JPEG válidos, tamanho excessivo, autenticação, CSRF, nome seguro,
publicação sem imagem e limpeza apenas da imagem nova quando o SQL falha.

`migrar-portal.py` prepara, compila e troca a cópia do portal, preservando o
original. Quatro grupos passaram: aplicação; segunda aplicação recusada;
reversão recusa edição posterior; reversão exata sem modificar a réplica original.
Não é um teste de perda elétrica. A cópia corrigida que recebeu tráfego sintético
tem SHA-256 `b286a5bdde86ec7f5c0a70d99ba994f65c86dfa1227df889f8b5f649d7bc3d5e`.

## Integrações homologadas nesta revisão

| Integração | Evidência | Limite |
| --- | --- | --- |
| ClamAV 1.4.3 + recebedor candidato | INSTREAM limpo, EICAR e ZIP; ameaça 554 sem armazenamento; motor indisponível produz 4xx sem armazenamento | daily.cld oficial copiado e assinatura EICAR de teste; não representa toda uma instalação antimalware atualizada |
| Triagem Santafé | Mensagem sintética de fisgada foi para Indesejadas | É componente nativo; não existe integração rspamd/spamassassin a aprovar neste percurso |
| Comunidade do portal | Uploads e falhas HTTP/SQL conferidos, usando portal capturado, identidade e banco sintéticos | Sem escrita nos dados ou estáticos reais |
| Certbot 2.1 + Pebble 2.10.1 | HTTP-01, certificado servido pelo SMTP TLS candidato, nova identidade após renovação, certificado vigente preservado com CA indisponível | CA local; não equivale a emissão pública Let's Encrypt |
| TLS público | Certificados dos dois portais com cadeia, nome e prazo verificados | Conferência de leitura dos serviços estáveis |
| SPF e política local | Candidato consultou DNS público; IP autorizado aceito e falsificação recusada | Não prova alinhamento de toda mensagem futura |
| DKIM público | 30 originais com 32 assinaturas não expiradas passaram; 30 cópias adulteradas foram recusadas | Mensagens da réplica; nenhum envio novo |
| DKIM expirado | 14 mensagens, 14 assinaturas expiradas, 14 recusas | Relógio e prazo não foram contornados para obter aprovação |
| Mailjet | STARTTLS verificado, SMTPUTF8/8BITMIME e AUTH 235 | Sem MAIL/RCPT/DATA; não comprova aceitação de mensagem nem entrega à caixa |

Os testes ClamAV/portal têm oito grupos; ACME, três; DNS/TLS/Mailjet, cinco.
Rede, PID e montagens dos aplicativos sintéticos são isolados; só loopback está
ativo. Chaves ACME e confiança são privadas. Não se instalou autoridade no
repositório de confiança do sistema. Nenhum certificado público foi alterado.
Binários Pebble vieram da versão oficial, com digest da distribuição conferido.

Referências dos contratos usados: [ClamAV](https://docs.clamav.net/manual/Usage/Scanning.html),
[Certbot](https://eff-certbot.readthedocs.io/en/stable/using.html) e
[Pebble](https://github.com/letsencrypt/pebble).

## Regressões e evidência herdada

macOS e Debian x86_64: dez etapas principais e onze subetapas, IBA/SDK em 14
grupos, instalação em cinco e operações/reversão em sete, além do gerenciador
de bibliotecas. Todas passaram. WebAssembly recompilado: 18 casos e recuperação
após erro passaram. Gramáticas foram testadas; não houve nova inspeção visual
das janelas nesta revisão. O conteúdo dos kits é comparado entre os sistemas
na selagem, sem comparar metadados dos arquivos ZIP.

A carga de uma hora e a migração da réplica completa pertencem à dados.12:
3600,39 segundos, 43.176 pedidos HTTP, 12 grupos e novas escritas preservadas
na reversão. Não foram repetidas nem atribuídas à dados.13. Essa evidência está
na entrega anterior e serve de referência, não substitui homologação de uma
promoção integral da dados.13 com todas as integrações habilitadas juntas.

Não foram homologados Windows/ARM, perda elétrica real ou nova publicação nos
editores. A carga prolongada do upload corrigido também não foi executada.
Disco foi acompanhado, preservando 2 GiB livres; somente dados sintéticos de
tentativas encerradas foram limpos. Captura, restauração e réplica real ficaram
intactas. Conteúdo postal, credenciais e registros privados permanecem no servidor.

## Tentativas corrigidas

- ClamAV: a primeira configuração tentava `initgroups` no namespace; retirado
  `User root` do clamd privado. A segunda falhou por nome de função HTTP no
  ensaio; corrigido. A terceira revelou o PNG truncado. A quarta passou.
- ACME: a primeira opção TLS do ensaio estava em caixa incorreta; a segunda
  atingiu a espera aleatória do Certbot. Corrigidas; terceira passou com a
  espera aleatória desativada apenas no ensaio, mantendo os testes de renovação.
- DKIM: corrigido identificador reservado no verificador antes de executá-lo.
  Assinaturas expiradas não foram consideradas comprovação de sucesso positivo.
- WebAssembly: o SDK instalado tinha cache sem permissão de escrita. Usado o
  cache privado já existente de homologação; segunda construção e testes passaram.

Essas tentativas não contam como aprovações.

## Pendências de promoção

O usuário não dispõe de subdomínio exclusivo para testar emissão pública.
Não é necessário parar Mailjet para homologar um envio isolado; falta indicar
uma caixa própria e confirmar recebimento. Nenhum envio foi realizado nesta
revisão. Esses itens permanecem explícitos no estado da entrega. Ainda será
necessário validar a promoção operacional conjunta antes de declarar estável.
Nenhum serviço de produção foi reiniciado e nenhum push, etiqueta ou catálogo
externo foi publicado. O núcleo operacional continua 2.1.0.
