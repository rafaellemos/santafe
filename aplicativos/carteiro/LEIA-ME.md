# Carteiro

**Estado estável:** Carteiro 1.5.0.

Carteiro é o núcleo postal voltado ao usuário: apresenta caixas, lista,
pesquisa, abre, organiza e posta cartas. Ele não recebe nem transporta SMTP.
A interface web desta primeira aplicação usa Caminheiro e vive sob
`/carteiro/`, em processo separado do site principal.

```text
navegador -> Nginx -> /carteiro/ -> Carteiro + Caminheiro :7100
                                   |             |
                                   |             +-- páginas e rotas HTTP
                                   +-- caixas e cartas
                                             |
                                             +-- Correio CD -> fila de envios
```

O núcleo em `bibs/bibf/carteiro.fé` não depende de HTTP. Outro adaptador pode
usá-lo futuramente em terminal, aplicativo gráfico ou dispositivo móvel.

## Responsabilidades

- reutilizar a autenticação web por `sf_sessao`;
- obter ou criar a caixa postal do usuário;
- listar as pastas Entrada, Todas, Enviadas, Rascunhos, Indesejadas e Lixeira;
  Arquivadas permanece como pasta física interna e compatível com IMAP, mas
  não ocupa uma entrada própria na navegação web;
- agrupar na interface as cartas de mesmo assunto, ignorando prefixos usuais
  de resposta e encaminhamento; o IMAP continua expondo cada carta e UID;
- paginar as pastas em blocos configuráveis, com 50 conversas por padrão,
  preservando a pesquisa ao avançar ou voltar;
- pesquisar, abrir, marcar como lida e mover cartas;
- abrir conversas com a carta mais recente permanentemente expandida e as
  anteriores recolhidas, com controles separados para expandir ou recolher
  somente as anteriores;
- selecionar todas, nenhuma, somente lidas ou somente não lidas na página;
- aplicar Marcar como lida, Marcar como não lida, Arquivar, Descartar ou
  Indesejada às
  cartas selecionadas na página ou a todas as correspondentes à busca;
- selecionar cartas na Lixeira e restaurá-las para a visão Todas;
- responder preservando `In-Reply-To` e `References` para encadear a conversa;
- encaminhar cartas, incluindo novamente os anexos originais pelo depósito;
- listar, por conversa, os participantes e os anexos das cartas agrupadas;
- visualizar imagens e PDFs em um quadro privado, com ações de baixar e
  imprimir, sem executar formatos ativos;
- recuperar do MIME imutável nomes longos de anexos repartidos conforme o
  RFC 2231, sem alterar o conteúdo armazenado;
- conservar remetentes confiáveis por caixa sem liberar conteúdo externo
  automaticamente;
- montar a postagem e enviá-la ao Correio CD;
- compor texto simples ou HTML reduzido, com títulos, listas, citações e
  ênfases saneados novamente no servidor;
- nunca executar automaticamente HTML ou anexos recebidos.

Recepção SMTP, distribuição, fila e transporte externo pertencem ao
[Correio](../correio/LEIA-ME.md).

## Arquivos

| Caminho | Papel |
|---|---|
| `carteiro.fé` | processo web |
| `fonte/carteiro/aplicação.fé` | rotas Caminheiro |
| `fonte/carteiro/páginas.fé` | apresentação HTML |
| `fonte/carteiro/web.fé` | adaptação HTTP e segurança de resposta |
| `estático/` | CSS e JavaScript |
| `operação/carteiro.service` | unidade systemd |
| `operação/nginx-carteiro.conf` | proxy de `/carteiro/` |

## Configuração

Copie `operação/carteiro.env.exemplo` para `/etc/santafe/carteiro.env`. O
serviço também lê `/etc/santafe/correio.env`, pois usa o diretório postal e o
CD. Segredos ficam apenas nesse segundo arquivo e nunca devem ser versionados.

Instalação esperada:

```text
/opt/carteiro/                              aplicação web
/etc/santafe/carteiro.env                  configuração da interface
/etc/santafe/correio.env                   diretório postal e banco
/var/lib/santafé/correio/                  objetos MIME e anexos compartilhados
/var/www/santafé.dev.br/carteiro/estático/ CSS e JavaScript
/var/log/santafé/carteiro.pulso             acontecimentos PULSO
```

O serviço roda como `carteiro`, mas participa do grupo suplementar `correio`
para ler os objetos com permissão `0660` no depósito `02770`. O MariaDB
conserva somente os metadados e os resumos criptográficos desses objetos.

## Rotas

- `GET /carteiro/entrada`, `/carteiro/todas` e as demais pastas;
- `POST /carteiro/lixeira/esvaziar`;
- `POST /carteiro/mensagens/acao-em-lote`;
- `POST /carteiro/mensagens/mover-para-lixeira`;
- `GET /carteiro/nova`;
- `POST /carteiro/enviar`;
- `GET /carteiro/mensagens/:id`;
- `POST /carteiro/conversas/:id/acao`;
- `GET /carteiro/conversas/:id/encaminhar`;
- `GET /carteiro/conversas/:id/imprimir`;
- `POST /carteiro/mensagens/:id/acao`;
- `GET /carteiro/mensagens/:id/imprimir`;
- `GET /carteiro/mensagens/:id/baixar`;
- `GET /carteiro/mensagens/:id/original`;
- `GET /carteiro/mensagens/:id/corpo-html`;
- `POST /carteiro/mensagens/:id/remetente/confiar`;
- `POST /carteiro/mensagens/:id/remetente/deixar-de-confiar`;
- `GET /carteiro/mensagens/:id/responder`;
- `GET /carteiro/mensagens/:id/encaminhar`;
- `GET /carteiro/mensagens/:id/anexos/:anexo`;
- `GET /carteiro/mensagens/:id/anexos/:anexo/visualizar`;
- `POST /carteiro/mensagens/:id/mover`;
- `GET /carteiro/estado`.

Ao responder, o Carteiro usa `Reply-To` quando a carta o fornece; caso
contrário, usa `From`. O compositor acrescenta o assunto `Resposta:`, cita o
texto original e envia os cabeçalhos `In-Reply-To` e `References`. A carta
continua passando pelo Correio CD e pela mesma fila durável dos novos envios.

Ao encaminhar, o destinatário fica em branco, o Carteiro acrescenta ao corpo
os dados legíveis da carta original e recupera novamente seus anexos pelo
depósito. O navegador recebe apenas as identificações da carta e nunca um
caminho de arquivo. A posse da carta é conferida outra vez no envio.

Entrada e Enviadas são determinadas pela direção e não podem ser cruzadas.
Uma carta recebida pode ir para Arquivadas, Indesejadas ou Lixeira e volta
para Entrada; uma enviada volta para Enviadas. Rascunhos não recebe cartas que
já foram enviadas ou recebidas. **Todas** é uma visão virtual das cartas
conservadas: não é destino de movimentação nem duplica linhas no banco.
Por isso, **Arquivadas** não aparece como botão no Carteiro: arquivar retira a
carta da Entrada e ela continua disponível em Todas. A rota e a pasta física
continuam presentes para interoperabilidade IMAP.
Essas regras existem na interface e no núcleo, portanto não podem ser
contornadas enviando manualmente outro nome de pasta ao servidor.

Nas pastas que conservam cartas, a barra postal mostra o intervalo exato e os
controles de atualização e paginação. O menu da caixa principal seleciona
todas, nenhuma, lidas ou não lidas da página. Cada linha e cada unidade do
contador representam uma conversa; a ação selecionada alcança todas as suas
cartas dentro do mesmo escopo da pasta. Depois da seleção aparecem as
ações Marcar como lida, Marcar como não lida, Arquivar, Descartar e
Indesejada em um único menu. Arquivar, Indesejada e Descartar também ficam
aparentes como atalhos ao lado desse menu. Descartar move as cartas para a
Lixeira sem apagá-las definitivamente e não abre uma pergunta; somente o
esvaziamento definitivo exige confirmação. Ao marcar
a página inteira, o usuário pode ampliar explicitamente o escopo para todas as
cartas da pasta ou busca. A lista integral é resolvida novamente no servidor;
o navegador não envia milhares de identificações. A operação exige proteção
CSRF e verifica a posse das cartas no núcleo. Excluir apenas move para a
Lixeira; a remoção definitiva continua reservada ao seu esvaziamento.
Os menus recolhem ao escolher uma opção, abrir outro menu, clicar fora deles
ou pressionar Escape. Sem seleção, as ações de alteração permanecem ocultas.

O leitor mostra uma conversa em cartões recolhíveis, mas a carta mais recente
e uma carta isolada permanecem abertas e não podem ser recolhidas. O resumo só
aparece nos cartões fechados. Neles, a primeira linha apresenta somente o nome
do remetente — ou o endereço quando não há nome —, o selo postal e a data curta
com dia da semana; o resumo ocupa a linha seguinte. O cabeçalho aberto apresenta nome, endereço,
destinatários, data completa, identidade SMTP, autenticação e Triagem em uma
caixa de detalhes. Cada carta oferece
Responder e Encaminhar no cabeçalho, além de excluir, marcar como não lida a
partir dali, bloquear, denunciar, filtrar, imprimir, baixar o arquivo `.eml`
e inspecionar o MIME original. O cabeçalho da conversa oferece Arquivar,
Indesejada, Descartar, marcar como não lida, mover, filtrar, encaminhar tudo,
imprimir tudo e os controles de expansão coletiva. A impressão usa um
documento autenticado e inerte que contém o corpo inteiro, independentemente
da altura visível do cartão; a caixa do navegador também permite salvar em PDF.

Imagens anexadas em PNG, JPEG, GIF e WebP e documentos PDF podem ser abertos
em uma visualização rápida, baixados ou impressos. A lista mostra até dois
anexos da conversa e resume o restante em **Mais**. A rota de visualização
exige a sessão e a posse da carta, usa `nosniff`, não permite cache
compartilhado e nunca torna SVG ou outros formatos ativos executáveis. O HTML recebido é
apresentado em um quadro isolado, sem programas, formulários, objetos,
conexões ou recursos externos. O usuário pode confiar no endereço exato do remetente, mas ainda
precisa confirmar separadamente o carregamento em cada carta. Essa confirmação
libera somente imagens HTTPS durante a abertura atual; programas, formulários,
objetos e conexões de programa continuam proibidos. Ligações somente abrem
após a ação do usuário. Todos os anexos permanecem disponíveis para baixar.

Na Lixeira, o botão **Esvaziar lixeira** pede confirmação e remove as cartas
definitivamente em uma transação, liberando a cota da caixa. A proteção CSRF
e a posse da caixa são verificadas antes da operação. As caixas de seleção
permitem restaurar somente as cartas escolhidas em **Todas**; internamente elas
voltam para Arquivadas, pois Todas é uma visão virtual. A retirada física de
objetos sem referência do Depósito é uma tarefa separada e conservadora.
Uma carta marcada com `\Deleted` por um cliente IMAP fica oculta no Carteiro
mesmo quando o cliente encerra a conexão antes de executar o expurgo.

## Limites iniciais

- um anexo de até 25 MiB por composição web;
- o compositor formatado usa apenas elementos textuais de uma lista positiva;
  atributos, estilos, programas, formulários e imagens são neutralizados no
  servidor mesmo quando o pedido HTTP é forjado;
- HTML preservado e renderizado em isolamento estrito pelo navegador;
- exclusão definitiva somente pelo esvaziamento confirmado da Lixeira;
- acesso IMAP protegido por TLS na porta 993; POP3 não faz parte desta etapa;
- o antivírus examina automaticamente a carta completa e os anexos antes da
  entrada ou da saída;
- a Triagem classifica cartas como regulares, suspeitas ou indesejadas e
  conserva pontuação e motivos no banco e no PULSO; o leitor cotidiano não
  exibe esse diagnóstico técnico;
- ligações mascaradas, destinos por IP, esquemas ativos, formulários de senha
  e pedidos de segredo combinados são explicados pela Triagem sem que o
  Carteiro abra ou consulte o destino;
- a página `/carteiro/triagem` cria regras por endereço ou domínio; a regra
  exata vence a regra de domínio e vale para cartas futuras;
- a decisão pessoal muda somente a pasta e fica separada da avaliação
  automática, da confiança em HTML, do antivírus e de SPF/DKIM/DMARC;
- SPF de entrada, verificação DKIM e DMARC são executados antes da Triagem;
  os resultados permanecem conservados para auditoria e aparecem somente na
  caixa de detalhes do remetente no leitor;
- reputação externa ainda não faz parte desta etapa.

Consulte a [arquitetura do ecossistema](../../docs/ARQUITETURA-DO-ECOSSISTEMA.md)
para as fronteiras entre Rede, Caminheiro, Correio, Carteiro e PULSO.
## Configuração de aparelhos

O caminho autenticado `/carteiro/configurar` apresenta as definições de
entrada e saída e oferece perfis Apple separados para iPhone/iPad e Mac. Os
perfis configuram IMAP em 993/TLS e SMTP em 465/TLS, usam o endereço postal
completo como nome de usuário e nunca incluem a senha. O aparelho pede a senha
durante a instalação.

Programas que implementam a descoberta do RFC 6186 também encontram os
registros `_imaps._tcp`, `_submissions._tcp` e `_submission._tcp` publicados
pela autoridade Nomes.
