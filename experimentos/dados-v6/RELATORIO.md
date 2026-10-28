# dados.6 — migração operacional, manual e carga

Rodada de 23/10/2026. **Candidato experimental; não é a versão maior estável.**
Base imutável: dados.5, SHA-256
`8b096db59c22939bdfb306a573ff01b9e6758e70683d7c2f7e94833378bb854f`.
Produção, bancos empresariais, serviços systemd/nginx, portal, catálogos,
perfis normais dos editores e Git remoto não foram atualizados.

## Correções

- O bombeamento da saída IMAP tentava remover o primeiro item mesmo quando a
  fila estava vazia. A remoção estrita do candidato revelava erro no callback
  assíncrono. Agora a fila vazia retorna antes de `tabela.remova`; o ensaio real
  exige ausência desse erro nos logs, além de verificar protocolo e banco.
- O manual candidato diferencia presença/nulo, exclusão explícita, listas
  densas, tabelas esparsas, JSON/ONFÉ, colares brutos e gabaritos. Linhas MariaDB
  são documentadas como listas, preservando NULL no meio e no fim. Corrigida
  também a descrição da anotação `--[[js]]`, aceita pelos recortadores.
- O executor do manual ainda apontava para WASM 2.0.3: a cópia de laboratório
  usa exclusivamente o WASM dados.6 compilado nesta rodada. Não altera o portal.
- A inspeção em 390 px encontrou tabelas de largura mínima 480 px expandindo a
  página para 502 px. A regra responsiva do manual candidato foi corrigida;
  a repetição mediu documento de 390 px em viewport de 390 px.
- O selamento das gerações cobre também arquivos de bibliotecas chamados
  `manifesto.json`; só o manifesto raiz de integridade é excluído do próprio hash.

## Migração operacional ensaiada

`operacao.py` cria somente laboratórios privados em `/tmp`: gerações seladas
com SHA-256 e permissões, trava exclusiva de escritor, journal, fsync e troca
atômica de um link. O consumidor resolve a geração uma vez ao iniciar e usa
essa mesma raiz para núcleo e módulos. Não deve reler o link para cada arquivo.
Dados persistentes ficam fora das gerações e não são apagados no rollback.

Os sete grupos passaram no macOS Intel e no Debian 12 x86-64:

1. Instalação completa da candidata; 300 leituras de saúde em três leitores
   concorrentes, durante 20 trocas entre núcleo estável 2.1.0 e candidata.
2. Recuperação após término abrupto antes da troca do ponteiro.
3. Recuperação após término abrupto depois da troca do ponteiro.
4. Retorno após falha de saúde pós-troca.
5. Segundo escritor recusado pela trava.
6. Alteração de manifesto interno de biblioteca recusada por integridade.
7. Arquivo adulterado recusado; hashes do estável e dados preservados.

**Limite:** a geração estável desse ensaio contém o núcleo real 2.1.0 copiado,
não uma réplica integral dos serviços empresariais. A candidata contém todos
os componentes instaláveis. Não houve migração de esquema/dados de negócio,
troca de serviço global, nem simulação de perda elétrica. O laboratório não
é um publicador pronto para produção.

O teste herdado de instalação também passou nos dois sistemas: caminho com
espaços, seis etapas reais de cópia, CLI/SLS/ONFÉ/módulos, reinstalação idempotente,
rollback após oito pontos de falha e remoção preservando arquivos alheios.

## Aplicativos e carga

Repetidos os 13 percursos reais descritos no relatório dados.5: Recebedor,
Agência, Envios, IMAP, Carteiro, autoridade e resolvedor Nomes, com MariaDB,
depósito, certificados, usuários e mensagens exclusivamente de laboratório.
Verificam autenticação, relay, CSRF, fila/entrega, MIME/anexo, COPY/EXPUNGE/APPEND,
Lixeira, persistência após reinício e fronteiras JSON/PULSO.

A carga concorrente durou pelo menos 60 segundos por sistema, sem desligar
limites de proteção. Cada execução persistiu 60 novas mensagens, fez 60 ciclos
SELECT/SEARCH IMAP, 1.200 consultas DNS UDP/TCP e consultas HTTP autenticadas e
anônimas. Depois, 65 conexões IMAP provocaram a proteção de frequência; a
recusa foi confirmada pelo evento PULSO, não presumida por qualquer erro TLS.

| Medida da execução final | macOS Intel | Debian 12 x86-64 |
| --- | ---: | ---: |
| Requisições HTTP | 1.595 | 2.361 |
| HTTP p95 | 107,97 ms | 75,13 ms |
| SELECT/SEARCH IMAP p95 | 24,79 ms | 27,29 ms |
| Envio SMTP p95 | 44,28 ms | 35,88 ms |
| RSS agregado máximo dos processos observados | 129.260 KiB | 228.192 KiB |
| Mensagens adicionais persistidas | 60 | 60 |

São medições de laboratório, não benchmarks comparativos entre sistemas nem
promessa de capacidade. O DNS registra lotes de 20 consultas, com pausas
deliberadas de 20 ms; sua duração não é latência de uma consulta. O limite de
memória observado foi inferior ao teto de segurança de 1 GiB. Isso não prova
ausência de vazamentos em horas/dias. As tentativas iniciais com tráfego sem
cadenciamento atingiram corretamente limites SMTP/IMAP/DNS; o ensaio foi
separado em carga dentro da política e sobrecarga intencional, sem relaxá-la.

## Regressões e manual

| Bateria repetida em dados.6 | macOS | Debian |
| --- | --- | --- |
| Núcleo 38, ONFÉ 34 e fronteiras PULSO/JSON | passou | passou |
| SLS 39 adversariais/incrementais + 39 LSP | passou | passou |
| SLS: 200 edições em documento de 1.502 linhas | passou | passou |
| Instalação e sete grupos de operação | passou | passou |
| 13 percursos de aplicativos + carga | passou | passou |
| Manual: estrutura, API e compilação dos 174 exemplos | passou | passou |
| Execução dos 3 novos exemplos e 9 exemplos JSON | passou | passou |
| WASM: 16 casos e recuperação após erro | — | passou |

SLS incremental: p95 de 6,58 ms no Mac e 11,56 ms no Debian; máximo de 22,42 ms
e 22,38 ms respectivamente. Cada resposta tinha limite de 15 segundos.
Manual: 1.245 IDs, 582 funções colapsáveis, 174 exemplos compilados,
262 contratos C e 344 contratos Fé. Compilar os 174 não significa executar
todos: os exemplos com efeitos externos não foram disparados indiscriminadamente.

A matriz ampla de bibliotecas/SQL/cadeia está registrada em dados.5; não foi
repetida integralmente nem contabilizada novamente nesta rodada. O único
ajuste funcional do runtime sobre essa base está no callback IMAP Fé.

## Conferência visual e editores

- Manual candidato aberto no navegador em loopback: desktop 1280 px e móvel
  390 × 844. Presença/exclusão, listas/JSON e colares/JSON executados pelo WASM
  candidato no navegador, com saídas corretas. Sem erros no console observado.
- Capturas `manual6-desktop.jpg` e `manual6-390.jpg` preservadas. O espelho usa
  CSS/imagens públicos somente em leitura; a fonte de ícones exibiu fallback
  textual nesta prévia. Isso permanece uma limitação visual, não é aprovação
  pixel a pixel de toda a página nem de todos os aplicativos.
- VS Code: 25 verificações com TextMate/Oniguruma e gramáticas reais HTML/JS,
  incluindo listas, ONFÉ, colares brutos e ®/Ⓡ NFC/NFD.
- Sublime: 17 verificações do recortador experimental real, incluindo Unicode,
  concatenações que interrompem atributos/comentários e 3.000 fragmentos.
- Esses dois últimos itens são regressões de tokenização/recorte. **A inspeção
  visual nativa dos editores não foi executada:** a superfície de aplicativos
  nativos está desabilitada nesta sessão. Nenhum editor instalado foi alterado
  e nenhuma aprovação visual foi inferida desses testes.

## Entrega e próximos gates

Fontes, manifesto SHA-256, WASM e evidências estão em `dist/candidato-dados-v6`.
O registro externo `ENTREGA.md` identifica o pacote final e o local verificado
no servidor. As árvores de teste foram `/tmp/santafe-dados6-aue6_a7e` no Mac e
`/tmp/santafe-dados6.IwWHd9ah/arvore` no Debian. Nomes herdados como
`aplicativos5.json`/`testar-instalacao.py` pertencem ao harness, não à versão
do núcleo executado; os testes conferem explicitamente dados.6.

Ainda impedem liberar a versão maior estável:

1. Fechar ABI e bytecode definitivos, incluindo política de rejeição/atualização.
2. Persistência atômica ONFÉ e política operacional de migração/retorno de dados.
3. Validar a cadeia de serviços atualizada a partir de uma cópia isolada completa
   da instalação estável, com publicador reversível e checagens de configuração.
4. Soak prolongado, cenários de saturação e dependências/provedores externos.
5. Inspeção visual nativa dos editores, revisão visual ampla dos aplicativos e
   plataformas ainda não ensaiadas (Windows/macOS ARM), conforme suporte prometido.

Pão do Café continua projeto independente: não foi incluído como aplicação
da plataforma, nem teve banco/configuração/depósito alterado. Não há comando
de publicação em produção nesta entrega.
