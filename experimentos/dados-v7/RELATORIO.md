# dados.7 — ONFÉ atômico e regressões

23/10/2026. Candidato experimental, **não versão maior estável**. Derivado da
base imutável dados.6. Não houve mudança de produção, banco empresarial,
serviço global, portal, catálogo externo, editor instalado, tag ou push.

## Implementação

- Decisão consolidada: listas não têm metatabelas nesta versão. Tabelas com
  comportamento podem conter listas; não se trata de funcionalidade prometida
  que falta implementar para este contrato.
- `onfé.grave` e `onfé.graveAssíncrono`: serialização antes de efeitos, com os
  limites e a recusa de código/ciclos/metatabelas do ONFÉ. Tipos de caminho e
  conteúdo validados sem coerção numérica silenciosa.
- Backend POSIX compartilhado no módulo `arquivo`: diretório aberto e fixado,
  temporário exclusivo, modo 0600, escrita completa, sincronização, renameat e
  sincronização do diretório. Operações antigas de arquivo não foram alteradas.
- Retorno distingue `inalterado`, `publicado` e `durável`. Uma falha posterior à
  troca não é apresentada como preservação da versão anterior. Não há retry ou
  rollback implícito que possa sobrescrever o trabalho de outro escritor.
- A versão assíncrona captura os bytes antes de agendar e devolve o contexto
  do chamador no laço principal. Falha no callback, inclusive erro não textual,
  é contida sem destruir a VM; as referências são liberadas.
- ONFÉ instalado também em bibf, via `importe "onfé"`. Manual e catálogo SLS
  incluem sete APIs ONFÉ e duas primitivas nativas de persistência. Instalação
  e desinstalação cobrem essa cópia, além da cópia interna do SLS.
- Invólucro WASM obriga a opção experimental e roda os testes: uma primeira
  construção sem essa opção foi recusada pelo teste de listas, não aprovada.

## Testes realmente executados

macOS Intel e Debian 12 x86-64, processos e dados próprios em /tmp:

| Bateria | Resultado |
| --- | --- |
| Persistência ONFÉ | 17 grupos passaram em ambos |
| Harness C com ASan/UBSan | mesmos 17 grupos passaram em ambos; sanitizadores no helper C, não em toda a VM |
| Núcleo / ONFÉ / fronteiras | 38 / 34 / fronteiras PULSO e JSON passaram |
| API antiga de arquivo | regressão passou |
| ABI experimental | módulo incompatível recusado; recompilado aceito |
| SLS | 39 testes + completude das novas APIs + 200 edições incrementais passaram |
| Manual | 174 exemplos compilados; 12 exemplos seguros executados; 264 contratos C e 351 Fé conferidos |
| Instalação privada | seis etapas, caminho com espaços, gravação ONFÉ instalada, idempotência, oito falhas/rollback, remoção seletiva |
| Gerações operacionais | sete grupos, incluindo 300 leituras durante 20 trocas, crash e trava |
| Aplicativos completos | 13 percursos, banco isolado, HTTP/SMTP/IMAP/DNS e persistência após reinício |
| Carga | 60 segundos por sistema, proteções mantidas; não é soak de horas |
| WebAssembly | compilado no Debian; 17 casos e recuperação após erro passaram |

Persistência: falhas de criação, permissões, escrita parcial/ENOSPC, retorno
zero de write, fsync do arquivo, fechamento, rename e fsync do diretório;
escritas curtas/EINTR; crash antes/depois da troca; troca do nome do diretório
pai; links, FIFO e diretório recusados; hardlink e descritor antigo preservados;
contexto/snapshot assíncrono, erro no callback, argumentos inválidos, UTF-8,
lista/tabela vazias e nulo armazenável. Quatro escritores fizeram 140 trocas
com três leitores concorrentes, sem conteúdo parcial. Ganchos de falha só
existem no executável de teste e não no módulo instalado.

Manual: 1.246 IDs, 582 funções colapsáveis. Nem todos os exemplos compilados
foram executados: exemplos de efeitos externos não são disparados livremente.
As falhas iniciais de caminho de módulos/quoting no harness e de entradas
ausentes no manual foram corrigidas, e as respectivas baterias repetidas.

## Limites e próxima etapa

A persistência não fornece transação entre arquivos, CAS, bloqueio de escritores,
sandbox, cancelamento/contrapressão de fila, preservação de ACL/xattrs nem prova
contra perda elétrica real ou volumes de rede. O diretório deve ser confiável.
Falha abrupta pode deixar temporário órfão; não há limpeza automática arriscada.
No WASM, persistência durável nativa é recusada explicitamente; dados e parser
continuam disponíveis. A leitura `carregue` não é confinada contra caminhos
hostis: não oferecer diretamente caminhos arbitrários a usuários remotos.

Ainda faltam para estabilizar a versão maior:

1. Fechamento da ABI/bytecode definitiva e política de atualização dos módulos.
2. Réplica isolada completa da instalação estável (serviços, configurações e
   dados), migração/retorno de dados e publicador operacional reversível. O
   teste de gerações atual usa somente o núcleo estável copiado como baseline;
   não equivale a migrar toda a instalação em produção.
3. Soak prolongado, saturação e provedores externos. A carga de 60 segundos
   não foi rebatizada de validação de longo prazo.
4. Inspeção visual nativa dos editores e aplicativos, além das plataformas
   prometidas ainda não ensaiadas, como Windows/macOS ARM.

A superfície nativa de aplicativos permanece indisponível nesta sessão; não
se declarou aprovação visual. Pão do Café continua independente e intocado.
Não há comando de publicação em produção nesta entrega.
