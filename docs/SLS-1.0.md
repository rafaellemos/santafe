# SLS 1.0 — contrato de evolução e bateria de aceitação

Estado em 21 de outubro de 2026: **1.0.0 publicado e conferido**.
O ponto de partida foi SLS **0.1.1** e núcleo publicado **2.0.3**. A versão
**1.0.0** (núcleo **2.1.0**) oferece intervalos precisos, sincronização
incremental e recursos semânticos; exige recompilar o núcleo com as APIs
`depure.analise` e `depure.lexemas` e o suporte POSIX privado do SLS.
Homologado nos hosts reais e visualmente nos dois editores em 21/10. As versões dos
pacotes VS Code e Sublime são independentes da versão do SLS.

Este documento organiza a atualização solicitada para o SLS 1.0. Primeiro
estabilizamos a experiência de desenvolvimento; o gerenciador e o catálogo de
bibliotecas foram implementados em seguida, com homologação separada.
Não se deve confundir a existência desta
bateria com a implementação das funcionalidades que ela exige.

## O que significa 1.0

Um servidor local, previsível, seguro e utilizável no VS Code e no Sublime,
com contrato documentado e os mesmos resultados nos dois clientes. O número
1.0 não exige implementar todo método opcional do LSP, nem transforma Santafé
em uma linguagem com tipagem estática. Exige cumprir o escopo abaixo, sem
inferir tipos ou destinos com uma certeza que a análise não possui.

Referência de protocolo:
[LSP 3.17](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/).
As capacidades só serão anunciadas quando a respectiva implementação existir.

## Componentes da entrega

| Componente | Contrato 1.0 | Situação inicial |
| --- | --- | --- |
| Transporte | JSON-RPC/stdio, limites, shutdown/exit, cancelamento e erros controlados | Base existente; carga/cancelamento longo pendentes |
| Documentos | Versões monotônicas, sincronização incremental, UTF-16, CRLF, URIs Unicode, arquivos não salvos | Sincronização integral existente |
| Analisador | Tokens e árvore com intervalos; recuperação após erros; escopos e vínculos de símbolos | Somente compilação sintática, sem execução |
| Diagnósticos | Intervalo preciso, código estável e mensagem em português; múltiplos erros quando recuperáveis | Primeiro erro por linha; coluna zero |
| Conclusões | Globais, bibliotecas padrão, C e Fé, aliases de `importe`, variáveis visíveis, membros estaticamente conhecidos | Recursos locais dos editores, não do SLS |
| Ajuda | Hover com documentação/assinatura/origem e ajuda do parâmetro ativo | Recursos locais limitados |
| Navegação | Definição, referências, símbolos de documento/projeto e destaques respeitando escopos | Ainda não oferecida pelo SLS |
| Refatoração | Preparar renomeação, validar nome e colisões; WorkspaceEdit revisável e versionado quando aplicável | Pendente |
| Projetos | Importações estáticas sem executar bibliotecas; cache invalidável, raízes isoladas, ciclos e limites | Pendente |
| Edição | Formatação idempotente, preservação de literais/comentários, correções rápidas conservadoras, dobramento e seleção estrutural | Pendente |
| Realce | Tokens semânticos para símbolos; `®` e `Ⓡ` distinguem expressão de texto | Realce sintático já existe nas extensões; tokens do SLS pendentes |
| Clientes | Encaminhar recursos ao SLS, negociar capacidades, evitar duplicatas com os provedores locais e permitir restart | Integração de diagnósticos existente |
| Distribuição | Instalação reproduzível, identificação do executável em uso, atualização e rollback documentados | Fluxo existente a homologar com a nova versão |

HTML/JS embutidos e a paleta suave dos editores são regressões obrigatórias:
concatenações podem interromper atributos e comentários, e os curingas podem
ocorrer em colares. O SLS não deve destruir esse realce nem tratar todo texto
embutido como código Santafé. Autocompletar/refatorar HTML ou JS com um servidor
dedicado dessas linguagens não faz parte deste contrato inicial.

## Ordem de implementação (histórico do plano concluído)

Progresso atual: os 39 critérios funcionais passaram, assim como os ensaios
adversariais de escopos, renomeação, múltiplos diagnósticos, cancelamento e raízes.
Os hosts reais do VS Code/Sublime, a inspeção visual em ambos e a instalação
macOS também passaram. Evidências em `HOMOLOGACAO-CONJUNTA.json`. Debian, instalação
com espaços, bibliotecas e WebAssembly passaram no ensaio isolado de 21/10.
A indexação e a análise sintática continuam integrais: não confundir
sincronização incremental com parser incremental. Detalhes em [SLS.md](SLS.md).

### 1. Base de análise e documentos — candidato 0.2

- Extrair/reutilizar regras do léxico real; evitar um segundo parser baseado
  somente em expressões regulares. Preservar intervalos de tokens, comentários,
  colares longos, concatenações e ambos os curingas.
- Representar offsets de octetos internamente com mapas de conversão para
  UTF-16. Grafema, ponto de código, octeto e coluna LSP não são intercambiáveis.
- Acrescentar alterações incrementais, caches por URI/versão e recuperação
  sintática sem executar o fonte. Manter compatibilidade com mudança integral.
- Melhorar intervalos de diagnósticos; não inventar uma coluna a partir da
  ocorrência textual de uma palavra na mensagem de erro do compilador.
- Introduzir limites de documento/projeto e processamento cancelável. Um laço
  síncrono que não lê novas solicitações não pode prometer cancelamento real.

Saída: diagnóstico preciso e base confiável para os demais recursos. Somente
depois desta implementação/homologação faz sentido atribuir a versão 0.2.

### 2. Símbolos, API e projetos — candidato 0.3

- Escopos de blocos, funções, parâmetros, variáveis locais, sombreamento e usos
  dentro de gabaritos; constantes/estruturas inferidas apenas quando seguras.
- Catálogo comum derivado dos mesmos contratos C/Fé usados no manual
  (`ferramentas/catalogo_editores.py`), ampliado com assinaturas/documentação.
  Não criar uma terceira lista divergente no SLS.
- Importações literais e aliases com resolução estática e caminhos documentados.
  Não carregar `.so`, executar módulos, avaliar configuração de projeto nem
  instalar dependências para descobrir sua API.
- Definições, referências, conclusões, hover, signature help e símbolos.
- Invalidar resultados após edição, salvamento, remoção e alteração de módulos;
  suportar múltiplas raízes sem mesclar projetos homônimos.

Saída: mesmos recursos semânticos nos dois editores, com testes de escopo e
importação passando diretamente no protocolo.

### 3. Refatoração, edição e integração — candidato 0.4

- Renomeação vinculada a símbolos, nunca substituição textual global. Recusar
  nomes inválidos, colisões e destinos dinâmicos ambíguos. Não alterar comentários,
  conteúdo literal ou símbolos de outro escopo. Incluir as interpolações.
- Formatação idempotente que preserva conteúdo de colares, comentários e CRLF.
  Correções de código devem ser apresentadas como edições revisáveis.
- Tokens semânticos, dobramento e seleção; limites entre Santafé e HTML/JS.
- VS Code: encaminhar pedidos ao servidor e negociar provedores locais como
  fallback, sem duas listas de conclusão simultâneas. Sublime: validar pelo
  cliente LSP a mesma matriz, além da edição sem servidor.

Saída: bateria automatizada do contrato-alvo aprovada e testes de integração
dos clientes verdes. Verde automatizado ainda não autoriza publicar 1.0.

### 4. Homologação e distribuição — candidato 1.0.0-rc

- Testes reais nos dois editores em perfis limpos; registrar comando e
  `serverInfo.version`, não somente a versão da extensão instalada.
- Instalação/atualização em macOS e Linux, incluindo prefixo de usuário e
  caminho com espaços. Windows deve ter teste próprio e suporte explicitamente
  declarado; não presumir que um launcher POSIX funcione nele.
- Benchmark com hardware, tamanho do projeto, latência p50/p95 e memória
  registrados; carga, cancelamento, memória após fechar documentos e restart.
- Fonte, instalado e pacote com versões coerentes, licenças e hashes; manual e
  instruções sem capacidades futuras descritas como disponíveis.
- Publicar candidato; promover a 1.0.0 só depois de resolver as falhas e anexar
  evidências. Não sobrescrever os artefatos históricos da Santafé 2.0.3.

## Bateria executável

Pré-requisitos: Python 3.9+ e núcleo compilado (`make cbin`). Nenhuma biblioteca
Python externa, rede, credencial ou instalação de produção é necessária.
Cada caso usa um processo SLS e um projeto temporário novos. O cliente de teste
é independente do cliente da extensão VS Code.

```bash
# Autoteste do verificador e regressão do perfil entregue:
python3 testes/integracao/testar_sls_infraestrutura.py
python3 testes/integracao/testar_sls_incremental.py
python3 testes/integracao/testar_sls_aceitacao.py --perfil atual

# Conferir os 39 critérios funcionais (não substitui os gates dos editores):
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 \
  --relatorio /tmp/sls-contrato-1.0.json

# Listar todos os critérios ou investigar um recurso:
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 --listar
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 \
  --caso renomeacao-segura-com-unicode

# Conferir um SLS instalado, sem alterá-lo:
python3 testes/integracao/testar_sls_aceitacao.py --perfil atual \
  --comando /usr/local/bin/santafé-sls
```

O catálogo de critérios vive em `testes/integracao/sls/casos.py`:

- 13 ensaios do perfil atual: identidade, erro/correção, salvar/fechar/reabrir,
  documentos homônimos, versões antigas, não execução de fonte/importações,
  Unicode, gabaritos/embutidos, parâmetros inválidos, rajada de 30 alterações,
  1.500 linhas e cancelamento de pedido inexistente.
- 26 ensaios adicionais do alvo: intervalos precisos, mudanças incrementais,
  conclusões, hover, assinatura, escopos, definição/importações, referências,
  quatro cenários de renomeação, importação sem efeitos colaterais, invalidação,
  símbolos, destaques, dobramento, seleção, formatação, correção e tokens.
- Autotestes do verificador: framing, Unicode, edições sobrepostas, timeout,
  limpeza de processo, classificação do relatório e servidor que anuncia
  capacidade mas devolve resposta vazia.

Os testes anteriores (`testar_sls.py`, `testar_sls_robustez.py` e os testes dos
editores) continuam obrigatórios. A bateria não substitui esses testes nem
alega esgotar a especificação LSP.

### Resultado e política de aprovação

- **OK:** comportamento exercitado e conferido, não apenas capacidade anunciada.
- **PENDENTE:** capacidade não anunciada. Nunca conta como sucesso ou `xfail`.
- **FALHA:** contrato exercitado não foi cumprido, houve erro ou timeout. No
  perfil 1.0 pode significar uma limitação conhecida do perfil antigo, não uma
  regressão recém-introduzida.
- Código de saída **0**: critérios selecionados aprovados; **1**: falha;
  **2**: capacidade pendente sem outra falha. `--caso` é uma execução parcial.
- `liberavel_como_1_0` permanece falso neste relatório automatizado. Os gates
  externos precisam de evidências separadas; não há opção para fingir aprovação
  visual ou de distribuição por linha de comando.

O relatório registra versão respondida por cada processo, comando, commit local,
árvore modificada, hash do fonte local, plataforma e duração. Quando `--comando`
aponta para outra instalação, o hash do repositório **não** prova os bytes do
servidor instalado. A procedência dos binários é outro gate.

`testar.sh` e o CI normal executam apenas a regressão do perfil entregue. O
workflow manual **SLS — contrato-alvo 1.0** executa o alvo em Ubuntu/macOS e guarda
os relatórios mesmo quando reprova. Não esconder a reprovação com `|| true`.

## Gates que ainda precisam de cobertura específica

A primeira bateria mede o caminho principal, mas a aceitação completa também
exige ensaios adicionais e revisão nestes pontos:

- Recuperação após vários erros no mesmo documento; importações cíclicas,
  aliases reatribuídos, metatabelas e exports dinâmicos ambíguos.
- Cancelamento de trabalho em andamento, arquivos excessivos, AST profundamente
  aninhada, memória e latência de projeto grande. O teste de 1.500 linhas é
  apenas regressão de desempenho, não uma certificação de escala.
- Isolamento de raízes, symlinks que saem do projeto, URIs remotas, configurações
  maliciosas e arquivos ainda não salvos. Sem downloads/comandos de workspace.
- Edits com versões concorrentes, colisões de rename e preservação de imports.
- Realce visual, snippets, Ctrl+B e Ctrl+Space nos dois editores; temas padrão,
  paleta suave, HTML/JS interrompidos por concatenação e curingas `®`/`Ⓡ`.
- Instalação limpa, atualização do SLS efetivamente em execução, catálogo dos
  editores, documentação pública e rollback.

Cada evidência deve identificar versão/hash testado, sistema/editor, procedimento,
resultado e limitações. Evidências da 0.1.1 ou de uma extensão anterior não
homologam automaticamente a nova 1.0.

## O que fica separado

| Área | Relação com esta entrega |
| --- | --- |
| Núcleo, compilador e bibliotecas | Preservar os contratos 2.x e usar a API real; não mudar semântica da linguagem para facilitar o editor |
| Depurador com breakpoints/passos/variáveis | Projeto próprio com DAP e suporte do runtime; diagnósticos de sintaxe não equivalem a um depurador |
| Gerenciador e repositório oficial de bibliotecas | Próxima etapa: manifesto, dependências, lockfile, integridade, resolução e instalação local de projeto |
| Integração futura do repositório com o SLS | Consumir metadados e caminhos já resolvidos; não executar instalação durante análise |
| Empresas que usam a plataforma | Pão do Café permanece independente; suas contas, dados e serviços não são fixtures desta bateria |

O encerramento da 1.0 é a soma de implementação, regressão, homologação real e
distribuição conferida — não somente uma troca de número de versão.
