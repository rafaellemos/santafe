# Candidato dados.11 — migração da instalação copiada

Revisão de homologação, derivada dos fontes selados dados.10. Não é publicação
estável. A identidade da IBA permanece `santafe-3`, com bytecode ESC SF3/0x30.
Não houve instalação operacional, alteração de configurações de produção,
reinício de serviços, push, etiqueta ou publicação de catálogos.

## Escopo e isolamento

A captura fornecida pelo operador contém 1.841 arquivos e os dois bancos
independentes. A restauração validou 13 tabelas por banco e 247 objetos postais
referenciados: 212 em Santafé e 35 em Pão do Café. Não faltou objeto.

As gerações estável e candidata executam em chroots privados, com namespaces
próprios de rede, PID e montagem. Não existe interface externa nem rota padrão.
Bibliotecas do sistema operacional e estáticos capturados são montados em
leitura. Os dois bancos e depósitos clonados são compartilhados pelas gerações
de teste, permitindo voltar à versão anterior sem apagar escritas posteriores.
Nenhum dump de banco, mensagem, configuração empresarial, credencial ou chave
privada de produção integra este pacote; os arquivos privados permanecem no
servidor. Esquemas SQL e certificados/chaves sintéticos dos testes fazem parte
dos fontes, sem credenciais de produção.

O Pão do Café participa como consumidor independente, com banco e configuração
próprios. Seus fontes não foram incorporados à distribuição Santafé.

## Correções e descobertas

1. **Verificador postal:** corrigida a comparação dos identificadores de objetos
   para BLAKE2b-256, algoritmo de `segredo.resuma`. SHA-256 continua correto para
   os manifestos de arquivos e do dump. O harness dados.10 confundia os dois
   contratos; a entrega selada anterior foi preservada com esta errata.
2. **Portal capturado:** `/entrar` sem destino produzia HTTP 500 já na geração
   2.1. O candidato normaliza o destino ausente antes de acessar o colar; os
   testes exigem 200 no candidato e registram 500 como defeito da baseline.
   O retorno à baseline reproduz esse defeito conhecido, sem escondê-lo.
3. **Expiração de limites:** a limpeza de `comunidade.limites` migrou de atribuir
   `nulo` para `tabela.apague`; o nulo agora armazenável não remove a chave.
4. **Instalação completa:** a geração candidata recebe também inicializador SLS,
   helpers nativos, gerenciador, cabeçalhos e pkg-config com IBA3. Não se conserva
   um auxiliar 2.1 ao lado do núcleo novo.
5. **Recursos do laboratório:** cópias repetidas esgotaram temporariamente o disco
   compartilhado. Foram removidas somente cópias de trabalho encerradas desta
   tarefa, preservando captura original e registros. O harness passou a exigir
   reserva de 2 GiB e montar estáticos somente em leitura, sem duplicá-los.
   Sete serviços operacionais consultados continuavam ativos após a limpeza;
   esse estado não comprova ausência de falhas transitórias durante o incidente.

Outras tentativas falharam por preparação do ensaio: caminho do chroot fora do
PATH, parâmetros da conta sintética, uma carta por execução da fila, variáveis
vazias indevidamente interpretadas como autenticação, dependências TLS não
capturadas, escaping Unicode, helpers/Node/gramáticas de referência ausentes.
As tentativas falhas não contam como aprovação e foram preservadas nos logs.

## Evidência

`ESTADO.json` e os resultados em `evidencias/` são a fonte de conclusão desta
entrega. Os nomes de alguns harnesses conservam `dados10`/`dados7`: foram
executados novamente contra os binários dados.11, e não copiados como aprovação.

- macOS e Debian x86_64: regressão em dez etapas e onze subetapas, IBA/SDK em
  14 grupos, instalação em cinco grupos e operações/rollback em sete grupos.
- Núcleo, ONFÉ atômico, SLS incremental, manual, bibliotecas e gerenciador;
  gramáticas e paletas de ambos os editores. Não houve nova inspeção visual
  das janelas: a camada visual não mudou; não chamar testes de gramática de
  aprovação visual.
- WebAssembly reconstruído no Debian: 18 casos e recuperação após erro.
- Captura/restauração adversarial: dez grupos sintéticos repetidos, incluindo
  corrupção, exposição de arquivo, traversal, symlink, banco/objeto ausentes
  e recusa de execução fora do namespace.
- Réplica: proxy nginx dos dois domínios, zonas DNS reais UDP/TCP e identidades
  DNSSEC, portal e Pão do Café, dois Carteiros, recebedor, agência SMTP, IMAP e
  duas filas. Login e mensagens novas usam contas sintéticas; as mensagens
  históricas são lidas integralmente e comparadas por hash, sem exportá-las.
- Ciclo: estável → candidata → estável, com novas escritas em cada fase,
  conferência de tabelas na inicialização e leitura integral após cada troca.
  Detalhes e contagens finais ficam no relatório sanitizado da réplica.

Rodada final: 23 grupos, 77 fontes finais compilados, 9.280 operações HTTP em
60,07s com seis clientes. Os 105 originais/16 anexos iniciais chegaram a
141 originais/22 anexos após as escritas de teste e o rollback; todas as leituras
comparadas por BLAKE2b-256. Rodada anterior sem a checagem final do SLS/SDK:
10.045 operações em 60,03s. Não somar rodadas como duração contínua.

Depois dos ensaios, as páginas iniciais e `/carteiro/estado` dos dois domínios
públicos responderam 200. O núcleo operacional continuava 2.1.0. Isso é uma
checagem pontual de saúde, não uma prova de ausência de impacto transitório
do incidente de disco. A versão candidata permanece restrita ao laboratório.

## Limites que continuam abertos

A carga desta réplica não é soak de horas. O HTTP 503 isolado do primeiro teste
dados.10 não voltou nas repetições, mas sua causa não foi demonstrada: permanece
aberto. Não promover a versão estável afirmando que essa falha foi corrigida.

TLS usa certificados de teste; não foram exercitados a cadeia pública nem a
renovação Let's Encrypt. Relay externo, autenticação DNS de remetentes,
antivírus e triagem externa foram desativados no percurso isolado. Estáticos
ficam em leitura; upload da comunidade não foi ensaiado. DNSSEC local conserva
as chaves, mas não revalida a delegação pública. Windows, ARM e perda elétrica
real não foram homologados. Definir explicitamente plataformas e gates da
versão estável antes da promoção.

O pacote permite revisar e reproduzir o candidato; não contém publicador de
produção. A passagem a produção continua dependente de homologação posterior.
