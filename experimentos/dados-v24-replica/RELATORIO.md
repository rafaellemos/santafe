# Dados.24 — migração coordenada da réplica completa

Rodada de 26/10/2026, concluída no Debian sem alterar a produção. Núcleo
3.0.0-rc.1, SLS e gerenciador 1.1.0-rc.1 são os binários dados.23 já testados:
os fontes C/H foram comparados antes da reutilização. Não houve mudança de
semântica nem nova compilação Windows nesta rodada.

## Resultado executado

- 22 grupos operacionais passaram na captura de 1.841 arquivos e dois bancos
  separados. Foram convertidos 73 fontes capturados e compilados 123 fontes
  da instalação preparada, incluindo bibliotecas e ferramentas novas.
- 247 objetos postais da captura tiveram sua integridade conferida. As
  leituras HTTP compararam o conteúdo integral de mensagens e anexos pelos
  hashes, antes/depois da troca e depois das reversões.
- Oito consumidores reais foram coordenados: portal, página Pão do Café,
  dois Carteiros, recepção SMTP, agência SMTP, IMAP e DNS. A fila de controle
  inicialmente inativa continuou inativa; os processadores das duas filas
  foram executados sob demanda apenas para as mensagens do ensaio.
- A transação trocou 86 arquivos na mesma raiz privada. A reversão explícita
  e a reversão por falha de saúde restauraram os arquivos e os estados ativos.
  A segunda falha foi provocada **depois** da entrada de novas mensagens nos
  dois bancos: essas mensagens, seus anexos e os demais dados sobreviveram.
- SMTPUTF8, STARTTLS, autenticação, compositor, login, envio nas duas filas,
  IMAP COPY/COPYUID, APPEND, exclusão da cópia, DNS UDP/TCP, DNSSEC e proxy
  HTTPS passaram no ambiente fechado. Identidades DNSSEC foram preservadas.
- A carga realizou **5.933 pedidos com seis clientes em 60,08 segundos**, sem
  erro HTTP. Não é uma medição de capacidade máxima nem a repetição da carga
  de uma hora da rodada dados.14.
- SLS, ajuda do gerenciador, SDK IBA3 e caminhos de módulos `3.0` foram
  conferidos na instalação candidata da réplica.
- Os 15 testes adversariais da transação, incluindo dez pontos de término
  abrupto, e o teste adicional dos destinos DNS passaram em macOS/Debian.
  O preparador recusou base corrompida e destino existente, preservando a
  sentinela. Não se simulou perda física de energia.

## Correções e ocorrência preservada

Foram integradas as correções semânticas de dados.23: remoção explícita de
campos de falha e limite expirado; os campos inicialmente ausentes continuam
ausentes. A liberação da variável local da chave DNS continua usando `nulo`.
Também foram integradas as correções anteriores do destino opcional e da
estrutura de imagens no upload. O upload não foi exercitado de novo nesta
rodada; a evidência anterior permanece identificada como dados.13/14.

O primeiro percurso parou **antes da troca** porque o plano incluía ambientes
DNS e a lista permitida admitia apenas seus arquivos Fé. A lista foi corrigida
para admitir `.env` nesses dois diretórios; as recusas de chaves, certificados,
SQL, depósitos e unidades globais permaneceram. O percurso completo foi
repetido. A tentativa anterior e seus dados foram compactados e conferidos,
sem apagamento da evidência.

A captura antiga reproduz HTTP 500 em `/entrar` sem destino na geração 2.1;
a candidata retorna 200. Ao reverter, restaura-se o comportamento histórico,
inclusive esse defeito conhecido. Não foi uma falha nova introduzida pela
migração.

## Isolamento e espaço

Rede sem saída, namespaces de processos/montagens e bancos/depósitos privados.
Os ambientes de banco/SMTP usam credenciais de ensaio. As identidades DNSSEC
da captura são lidas somente na cópia privada e ficam no servidor, assim como
os demais arquivos privados e mensagens.
Todos os processos de laboratório foram encerrados. O espaço livre ao final
foi de 2.492.919.808 bytes, acima da reserva de 2 GiB.

Antes do ensaio, três laboratórios sintéticos já encerrados foram compactados;
conteúdo e modos dos 1.325 membros foram conferidos antes de liberar os
diretórios. Os arquivos recuperáveis continuam no servidor. Nenhuma captura,
pacote selado, banco operacional ou VM foi removido.

O núcleo **2.1.0** e os sete processos de produção mantiveram seus hashes/estado
de início; quatro rotas públicas retornaram 200 após a bateria. Sem reinício,
publicação de catálogo, etiqueta ou push nesta rodada.

## Limites para a versão estável

Esta é uma captura histórica, não uma captura atualizada imediatamente antes
da publicação. O supervisor testado controla processos privados, não o
systemd global. O publicador de produção ainda precisa adaptar essa fronteira
e validar a instalação atual sem restaurar bancos sobre mensagens novas.

Mailjet/ACME públicos, ClamAV e autenticação DNS externa não foram repetidos.
A evidência Windows continua vinculada ao MSI dados.21; precisam ser
reconstruídos e ensaiados os pacotes com os caminhos/identidades `3.0`.
Os pacotes oficiais dos editores ainda precisam dessa consolidação.
Assinatura pública permanece pendente; validação auditiva foi adiada pelo
usuário. Nenhum desses itens foi declarado aprovado nesta rodada.

O candidato dados.24 está pronto para revisão do ensaio operacional. **Não há
comando de publicação em produção nesta entrega.**
