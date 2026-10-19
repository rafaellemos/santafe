# Histórico de alterações

## 2.0.2 — fechamento em 2026-10-19

Revisão corretiva da linha 2.0, sem novas funcionalidades nesta etapa de
fechamento. A instalação no servidor é uma etapa separada do registro Git;
consulte [as notas de entrega](docs/LANCAMENTO-2.0.2.md).

- versão pública do executável corrigida; layout de bibliotecas e ABI preservados;
- grafemas Unicode 17.0.0 com tabelas oficiais, GB9c e ensaio de todas as fronteiras;
- separador binário de `colar.junte` e precisão inteira de `tabela.maiorÍndice`;
- SLS 0.1.1: ciclo de vida, erros JSON-RPC, limite de cabeçalho, versões de documento;
- VS Code 1.0.6 e Sublime 1.0.13: correções já homologadas de SLS, edição,
  catálogo C/Fé com 610 entradas, gabaritos ®/Ⓡ e HTML/JS concatenados;
- paleta suave opcional para HTML/JS e correção da herança de estilo dos gabaritos;
- instalação sem sucesso falso, sem REPL final e sem modificar `/etc/gai.conf`;
- fonte do manual versionado em `docs/`, empacotamento NFC e testes independentes de chaves locais;
- ensaios de integração MariaDB atualizados e configuração inicial de CI;
- suítes aprovadas em macOS e Debian, com MariaDB isolado; verificação gráfica
  dos editores concluída em macOS Intel;
- distribuição inclui o runtime Oniguruma do VS Code, antes omitido pela
  exclusão genérica de arquivos WebAssembly; licenças preservadas;
- documentação e publicação reversível consolidam núcleo 2.0.2, SLS 0.1.1,
  manual, downloads e executor WebAssembly, sem modificar bancos ou aplicações empresariais.

## 2.0.1 — 2026-10-17

Correção do instalador local, sem alteração da linguagem, da ABI C ou do
contrato do SLS.

- as dependências, a compilação e a instalação agora são executadas em
  primeiro plano, com sua etapa e saída visíveis;
- o instalador guiado não repete dependências nem chama o Homebrew como root;
- a instalação preserva a compilação como usuário comum e só usa `sudo` ao
  copiar arquivos para `/usr/local`.

## 2.0.0 — 2026-10-17

Primeiro lançamento estável da linha 2.0. Ele consolida as mudanças de
vocabulário, Unicode e ferramentas preparadas nas prévias públicas.

### Incluído

- SLS 0.1.0 distribuído com o núcleo, por `santafé-sls`, para diagnósticos
  sintáticos locais sobre LSP/stdio;
- extensões oficiais 1.0.0 para Visual Studio Code e Sublime Text, com realce,
  snippets, conclusões da API pública, ajuda rápida e navegação local de
  funções;
- distribuição canônica para Sublime Text como `Santafe.sublime-package`;
- `tamanho` e `colar.tamanho` contam grafemas em colares; `octetos` e `#`
  medem bytes de colares; `tabela.maiorÍndice` nomeia a maior chave numérica
  positiva de tabelas esparsas;
- `json.matrizVazia`, para representar explicitamente `[]` ao codificar JSON.

### Compatibilidade

- o fonte 2.0 não é compatível com 1.0 onde usa `lógico`, `_AMBIENTE` e a nova
  medida de `tamanho`; siga o guia de migração;
- o SLS 0.1.0 diagnostica sintaxe. Análise semântica entre arquivos, tipos,
  referências, formatação e depuração continuam fora do escopo desta versão.

## 2.0.0-preview.2 — 2026-10-17

Correção da primeira publicação da prévia para tornar a extensão do Visual
Studio Code imediatamente útil, mesmo antes de o SLS possuir análise semântica.

### Incluído

- extensão Santafé para VS Code 0.2.0, com ícone próprio e catálogo das 344
  entradas da API pública;
- conclusões para palavras reservadas, bibliotecas, funções globais, API pública
  e símbolos declarados no arquivo aberto;
- ajuda ao passar o mouse, estrutura de funções no explorador e navegação para
  declarações de funções no próprio arquivo;
- gerador do catálogo da extensão a partir de `docs/API-PUBLICA-FE.tsv`, para
  que o pacote não acumule uma lista manual divergente da API publicada.

### Limites conhecidos

- o SLS continua em 0.1.0 e fornece diagnósticos sintáticos; conclusões
  semânticas entre arquivos, inferência de tipos, referências, formatação e
  depuração pertencem às próximas etapas do servidor de linguagem.

## 2.0.0-preview.1 — 2026-10-17

Prévia pública para desenvolvimento e homologação da próxima versão maior.
Ela não substitui a linha estável 1.0.0 em ambientes de produção.

Esta versão consolida o vocabulário público em português. Ela é
incompatível no nível do fonte com a versão 1.0.0 nos pontos descritos
abaixo. A ABI C herdada continua identificada pelo número `503`; isso não
representa compatibilidade de sintaxe ou vocabulário.

### Alterações incompatíveis

- `tipo(verdadeiro)` e `tipo(falso)` agora devolvem `"lógico"`, em vez de
  `"booleano"`;
- `_AMBIENTE` substitui `_ENV` como nome especial do ambiente léxico;
- `_ENV` passa a ser um identificador comum e não existe apelido automático
  de compatibilidade;
- comparações textuais de tipos em bibliotecas e aplicações devem usar
  `"lógico"`.
- para colares, `tamanho` e `colar.tamanho` passam a medir grafemas UTF-8,
  não bytes; para tabelas, `tamanho` segue a medida estrutural de `#`, sem
  percorrer todas as chaves. Código que mede dados binários deve usar
  `octetos`.

### Incluído

- SLS 0.1.0: servidor de linguagem Santafé por LSP/stdio, com sincronização
  integral de documentos e diagnósticos sintáticos em tempo real. É distribuído
  pelo comando `santafé-sls` junto com o núcleo.
- `json.matrizVazia`, marcador explícito para codificar uma matriz JSON vazia
  (`[]`) sem confundi-la com o objeto vazio (`{}`).
- teste de regressão do vocabulário nos executores nativo e WebAssembly;
- [guia de migração do vocabulário](docs/MIGRACAO-VOCABULARIO-LOGICO.md).
- `octetos(s)`, medida explícita dos bytes de um colar.
- `tabela.maiorÍndice(t)`, nome claro para localizar a maior chave numérica
  positiva em tabelas esparsas. O nome histórico `tabela.maiorN` foi
  removido antes da versão maior.
- `colar.descompacte(s [, máximo])` limita a saída a 64 MiB por padrão; o
  limite pode ser declarado explicitamente em tarefas que realmente exigem
  arquivos maiores.

## 1.0.0 — 2026

Primeira versão pública estável do Santafé.

### Incluído

- núcleo derivado de Lua 5.3.6 com sintaxe e biblioteca padrão em português;
- suporte nativo a UTF-8 e gabaritos literais;
- compilação e instalação validadas em macOS e Debian GNU/Linux;
- bibliotecas C `rede`, `mariadb`, `segredo` e `tomada`;
- bibliotecas Santafé `bit32`, `caminheiro`, `imagem`, `rpdf` e `turing`;
- compilação WebAssembly;
- exemplos e testes de integração.
