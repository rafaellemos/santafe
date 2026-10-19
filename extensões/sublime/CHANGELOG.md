# Registro de mudanças — Santafé para Sublime Text

## 1.0.13 — 18 de outubro de 2026

- Realce da API C/Fé gerado do catálogo público, incluindo JSON; chamadas locais e métodos.
- `função` ciano itálico no Monokai; gabaritos laranja sem itálico.
- Expressões `®{…}`/`Ⓡ{…}` deixam de herdar o escopo amarelo do colar.
- Paleta suave opcional para HTML/JS, reversível pela paleta de comandos.
- Preservação de concatenações, SLS, snippets e configurações dos demais idiomas.

## 1.0.12 — 18 de outubro de 2026

- Preserva atributos HTML e comentários JavaScript entre literais concatenados,
  inclusive com delimitadores diferentes, aspas escapadas e expressões agrupadas.
- Recorta os literais sem executar código e usa as gramáticas nativas em um
  documento virtual; as expressões intermediárias e os curingas `®`/`Ⓡ` ficam
  sob a gramática Santafé.
- Aplica as cores por regiões de primeiro plano, com fundo transparente nos
  cinco esquemas nativos. Documenta a regra necessária para esquemas próprios.
- Limita o trabalho, descarta resultados obsoletos e limpa as regiões ao editar,
  fechar a aba ou descarregar o pacote. Não depende de Node nem de LSP.
- Validação nativa no Sublime 4215: 43 verificações novas de concatenação e
  55 regressões de realce; cinco esquemas, edição e cancelamento conferidos.

## 1.0.11 — 18 de outubro de 2026

- Reconhece `<!doctype>` sem exigir maiúsculas.
- Realça fragmentos concatenados que começam com texto antes da marcação HTML,
  como `[[ | Pão do Café</title>]]`, sem procurar tags fora do colar atual.
- Inclui regressões do cabeçalho completo e de `escapeHTML` com aspas alternadas.

## 1.0.10 — 18 de outubro de 2026

- Realça o token completo `®var`/`Ⓡvar`, incluindo o curinga, como variável.
- Realça `®{` e `}` como delimitadores de interpolação com estilo de operador,
  sem herdar a cor do colar; mantém o realce interno da expressão.

## 1.0.9 — 18 de outubro de 2026

- Registra Enter em `Default.sublime-keymap`; funções sem `início` opcional
  recebem recuo e `fim`, confirmado com a tecla real no editor.
- Realça `®var`, `Ⓡvar` e expressões com chaves aninhadas.
- Incorpora HTML e JavaScript em colares, com anotações opcionais para conteúdo
  multilinha; usa herança e `embed` para evitar recursão de `with_prototype`.
- Corrige a variável interna da gramática para realçar funções nativas.

## 1.0.8 — 17 de outubro de 2026

- Consolida a candidata 2.0.2: catálogo da API C/Fé, execução por argumentos
  separados e procura do núcleo nos prefixos de instalação.

## 1.0.7 — 17 de outubro de 2026

- Adiciona **Santafé: Ativar diagnósticos SLS** à Paleta de Comandos.
  O comando localiza o SLS instalado, grava a configuração do servidor e pede
  ao Package Control a instalação do cliente LSP; não exige editar arquivos
  de preferências.
- Atualiza o exemplo para o formato atual
  `LanguageServers.sublime-settings` do cliente LSP.

## 1.0.6 — 17 de outubro de 2026

- Fecha com `fim` ao pressionar Enter depois de um cabeçalho completo de
  `função`, `se`, `para` ou `enquanto`.
- Corrige os limites Unicode do realce: `e`, `ou` e demais palavras reservadas
  não são mais reconhecidas dentro de identificadores como `índice`.

## 1.0.5 — 17 de outubro de 2026

- Indenta automaticamente blocos iniciados por `função`, `se`, `para`,
  `enquanto`, `senão` e `repita`, e reduz o recuo em `fim`, `senão` e `até`.
- As conclusões de `função`, `se`, `para`, `enquanto` e `repita` agora inserem
  um gabarito com fechamento correspondente.

## 1.0.4 — 17 de outubro de 2026

- Inclui `.python-version` no arquivo distribuído. Isso contorna um defeito
  do Package Control 4.2.8 que impede instalar extensões de repositórios
  externos no host Python 3.14 do Sublime Text 4215.

## 1.0.3 — 17 de outubro de 2026

- Publica o catálogo e os arquivos de instalação por URLs totalmente ASCII,
  com o caminho estático percentuado, para que o Package Control baixe o
  pacote sem depender de interpretar caracteres fora do ASCII.

## 1.0.2 — 17 de outubro de 2026

- Declara compatibilidade com os hosts Python 3.3, 3.8 e 3.14 do Sublime
  Text, permitindo que o Package Control escolha o host disponível em cada
  versão do editor.

## 1.0.1 — 17 de outubro de 2026

- Adiciona distribuição pelo repositório HTTPS oficial do Santafé para o
  Package Control.
- Produz um arquivo versionado, sem `package-metadata.json`, adequado ao
  instalador do Package Control.
- Mantém o arquivo canônico `Santafe.sublime-package` para instalação manual.
- Renomeia o arquivo interno do trecho de função para ASCII, preservando o
  gatilho `função` e evitando problemas com extratores em Windows.

## 1.0.0 — 17 de outubro de 2026

- Primeira versão pública: sintaxe, trechos, conclusões locais e da API,
  ajuda ao repousar o cursor, build e integração opcional ao SLS.
