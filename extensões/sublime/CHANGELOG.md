# Registro de mudanças — Santafé para Sublime Text

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
