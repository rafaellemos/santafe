# Persistência ONFÉ — contrato candidato dados.7

Listas permanecem sem metatabelas nesta versão, por decisão de linguagem.
O candidato não instala nem muda a produção.

`importe "onfé"` é instalado também como biblioteca Fé pública. `cod`, `decod`,
`carregue`, `deJSON` e `paraJSON` mantêm o contrato. Novas operações:

```santafé
local O=importe "onfé"
local ok,falha,estado=O.grave("configuração.onfé",{telefone=nulo,itens=[]})
-- ok=verdadeiro, falha=nulo, estado="durável" em sucesso.
```

`graveAssíncrono(caminho,dado,tratador,contexto)` captura a serialização antes
de agendar E/S na piscina GIO. Retorna verdadeiro ao agendar (não ao persistir).
Chama `tratador(ok,falha,estado,contexto)` uma vez, no laço principal. Mantenha
a VM e o laço vivos até terminar. A codificação é síncrona e limitada a 4 MiB;
a versão `grave` bloqueia e é destinada a CLI/configuração, não ao laço servidor.

Dados inválidos/cíclicos/com metatabela e argumentos inválidos geram erro antes
de alterar o destino. Erros de E/S retornam nulo, mensagem e um destes estados:

| Estado | Significado desta tentativa |
| --- | --- |
| inalterado | Esta tentativa não trocou o destino. Outro escritor pode tê-lo alterado. |
| publicado | A troca ocorreu, mas a confirmação de durabilidade falhou. Não presumir rollback nem repetir cegamente. |
| durável | Conteúdo e diretório sincronizados com êxito segundo o sistema de arquivos. |

Um temporário exclusivo no mesmo diretório recebe todo o conteúdo, modo 0600,
sincronização, fechamento, renameat e sincronização do diretório. Leitores que
abrem o destino veem o arquivo anterior ou o novo completo. Um descritor já
aberto continua no arquivo anterior. Os caminhos são relativos ou absolutos;
o diretório pai deve existir e ser confiável. É resolvido uma vez e mantido
aberto durante a operação. Links em ancestrais são aceitos: **não é sandbox**.
O destino existente precisa ser arquivo regular, não link, FIFO ou diretório.
O arquivo novo pertence ao processo, modo 0600; não preserva ACL, xattrs,
proprietário/modo antigos nem altera os demais nomes de um hardlink.

Vários escritores podem substituir arquivos inteiros: a última troca vence.
Não há trava, CAS ou transação de leitura-modificação-gravação. Quem precisar
disso deve serializar seus escritores. Não há transação entre vários arquivos.
Uma falha capturável remove somente o temporário criado por essa chamada.
Término abrupto antes da troca pode deixar `.onfe-UUID.tmp`; não é carregado
automaticamente nem removido por heurística que possa atingir outro escritor.

`carregue` lê o arquivo, não executa código, mas não confina caminhos e não é um
leitor endurecido contra arquivos especiais/links. Use arquivos de dados sob
controle da aplicação. Retornar binários antigos não converte dados novos:
preserve uma cópia anterior antes de uma migração de esquema; restaure dados
e consumidor de forma coordenada. Não sobrescreva dados de negócio neste ensaio.

A garantia é POSIX, testável em macOS/Linux. Não constitui prova de perda de
energia real, hardware defeituoso ou semântica de volumes de rede. No WASM,
codificação e leitura virtual continuam disponíveis, mas persistência durável
sem o módulo nativo é explicitamente indisponível. Windows não está homologado.
