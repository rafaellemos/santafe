# Dados.14 — validação operacional conjunta concluída

Pronto para homologação; não aprovado para promoção estável. Concluído em
24/10/2026. Base imutável dados.13, SHA-256 dos fontes:
`dfed0891450d6b0465c2c2db3fc9013029c948a385a17ae6c11885bb807ece52`.
IBA `santafe-3`; SLS `1.0.0-dados.14`; kits experimentais `0.0.14`.
Nenhuma funcionalidade nova foi acrescentada à linguagem nesta revisão.
Listas, nulo armazenável, ONFÉ e colares brutos `[=[...]=]`/`[==[...]==]`
conservam o contrato aprovado. Listas continuam sem metatabelas.

## Ensaio integrado na réplica completa

Os 21 grupos passaram com os sete aplicativos capturados, MariaDB, nginx,
DNS/DNSSEC, SMTP/IMAP, retransmissor TLS/AUTH privado, ClamAV e Certbot/Pebble.
Não há rota de saída; o SMTP do ensaio recusa destinatários externos. Bancos,
credenciais e mensagens capturados permaneceram no servidor. O Pão do Café
foi ensaiado como projeto separado e com seu banco isolado, não incorporado
à distribuição da plataforma.

- Leitura inicial: 165 originais, 24 anexos e 44 páginas; ao final, 187 originais,
  os mesmos 24 anexos e 44 páginas, incluindo novas mensagens sintéticas.
- SMTP AUTH/STARTTLS, filas, compositor, login e IMAP passaram nos dois bancos,
  antes e depois da renovação. Saídas tiveram SPF/DKIM/DMARC verificados no destino.
- Falsificação SPF/DMARC e EICAR foram recusados; indisponibilidade do antivírus
  produziu falha temporária; a mensagem sintética de fisgada foi classificada.
- Upload truncado e CSRF inválido recusados; imagem válida persistida. A correção
  estrutural é a da dados.13, cujo relatório descreve seus limites de validação.
- DNS real capturado foi conferido em UDP/TCP: duas zonas e quatro respostas
  assinadas. Chaves da captura foram preservadas.
- Aos 120 segundos de carga, o certificado foi renovado pela CA local. O nginx
  apresentou o novo certificado sem interromper os leitores. Após a carga,
  os consumidores postais da réplica foram reiniciados e ensaiados com ele.
- A reversão retornou à cópia estável preservando tabelas, originais, anexos e
  novos uploads. Não se instalou nada em produção.

## Carga prolongada

| Medida | Resultado |
| --- | ---: |
| Duração | 3600,42 s |
| Leitores | 6 |
| Pedidos HTTP concluídos | 43.176 |
| Limite imposto | 12 pedidos/s |
| Percentil 95 | 53,64 ms |
| Amostras de recursos | 718 |
| Pico de RSS agregado | 1.079.228 KiB (1053,93 MiB) |
| Menor espaço livre | 2437 MiB |
| Máximo de registros | 46.019.211 bytes |
| Máximo de descritores | 308 |

Não houve falhas de pedidos. A carga exercita leitura HTTP nos dois Carteiros;
não mede capacidade máxima, saturação, envio SMTP contínuo ou upload contínuo.
Reservas fixadas antes da execução: 2 GiB de disco, crescimento até 256 MiB,
RSS até 1536 MiB incluindo ClamAV/CA, memória disponível mínima 768 MiB,
registros até 128 MiB e 2048 descritores. Amostragem nominal a cada cinco segundos.
O orçamento anterior de 800 MiB não incluía os processos ClamAV e CA.

## Imagens após reversão

O roteiro principal confere hashes de uploads temporários; só isso não comprova
leitura pela página. O complemento `imagens-reversao.py` passou em seis grupos:
montou uma cópia privada das imagens no caminho estático de cada chroot,
conferiu as referências das postagens e leu cinco arquivos por HTTPS nas duas
gerações (uma imagem capturada e quatro uploads sintéticos acumulados).
Os bytes e os bancos permaneceram iguais. O complemento não integra a medição
de uma hora e não grava no diretório estático original.

## Regressões e distribuição

macOS e Debian x86_64: dez etapas principais e onze subetapas; IBA/SDK em 14
grupos; instalação em cinco; operações/reversão em sete; gerenciador de
bibliotecas. Todos passaram. WebAssembly foi recompilado e passou em 18 casos
mais recuperação após erro. O manual foi validado novamente nos dois sistemas
após atualizar a referência das extensões estáveis para 1.1.1 e distinguir
critérios de promoção de evidências herdadas.

Os kits contêm 47 entradas. Em relação à dados.13 mudaram apenas versão e
READMEs; gramáticas e implementação são iguais. Não houve nova inspeção visual
das janelas nesta revisão. Testes de gramática não equivalem a teste visual.
A entrega inclui manifesto dos fontes, diferenças em relação à base e evidências
sanitizadas; não inclui bancos, registros privados ou credenciais operacionais.

## Tentativas e correções do ambiente de ensaio

Tentativas r1–r6 não contam como aprovação. Foram corrigidos apenas os auxiliares:
ClamAV passou a usar temporários permitidos pelo perfil AppArmor existente;
DNS privado passou a responder negativamente às consultas de ancestrais DMARC;
GIO/AI_ADDRCONFIG exigiu interface dummy no namespace, sem gateway nem rota
externa; comparação de domínio do retransmissor passou a ser literal, pois
hífens interpretados como padrão faziam a autorização retornar nulo e aguardar.
A execução r7 concluiu os 21 grupos. Os diagnósticos das tentativas ficaram no
servidor. A primeira regressão Debian parou porque Node não estava no PATH;
a segunda passou com o Node do SDK, sem remover testes.

## Produção e evidência Mailjet

A produção permaneceu 2.1.0. Hash do núcleo e identidade/tempo de início dos
sete processos são os mesmos antes e depois; quatro rotas públicas responderam
HTTPS 200. Nenhum serviço, configuração ou certificado público foi alterado.
Não houve push, etiqueta nem publicação em catálogos externos.

O envio único autorizado pelo Mailjet pertence ao complemento dados.13. O SMTP
aceitou a mensagem, o provedor registrou sent e o usuário confirmou recebimento
com acentos corretos. Não foi enviado outro e-mail nesta revisão. Isso comprova
aquele percurso e aquela mensagem, não aceitação por todos os provedores nem
posição na caixa de entrada. A entrega selada dados.13 permaneceu imutável.

## Limites de promoção

A emissão pública ACME não foi homologada: não há subdomínio exclusivo de teste.
Certbot/Pebble local não substitui emissão pública. Windows/ARM, perda elétrica
real e nova inspeção visual não foram executados nesta revisão. Esses limites
permanecem explícitos em ESTADO.json; não há promoção estável automática.

A cópia estável reproduz HTTP 500 previamente observado em `/entrar` sem destino;
o candidato responde 200. O ensaio registra ambos. Reversão significa retorno
à base capturada, com dados preservados, não correção retroativa desse defeito.
Os fluxos de login com destino foram verificados separadamente.
