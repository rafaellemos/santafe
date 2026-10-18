# Santafé para Sublime Text

Pacote oficial 1.0.8 para Sublime Text 4 (build 4107 ou superior).

Ele reconhece `.fé` e `.fe`, aplica realce de sintaxe, oferece snippets,
conclusões da linguagem e da API pública, exibe ajuda curta ao repousar o mouse
sobre uma função conhecida, indenta estruturas de bloco e integra execução e
verificação sintática no menu **Tools → Build System**.

Depois de escrever um cabeçalho completo, por exemplo
`para índice = 1, 10 início`, pressione Enter para abrir o corpo já fechado
por `fim`. Os snippets continuam disponíveis ao escolher uma conclusão ou usar
Tab sobre o gatilho `para`, `se` ou `função`.

## Instalação recomendada: Package Control

No Sublime Text, abra a Paleta de Comandos (`Ctrl+Shift+P` ou `⌘⇧P`) e execute
**Package Control: Add Repository**. Informe uma única vez:

`https://xn--santaf-gva.dev.br/est%C3%A1tico/sublime/packages.json`

Depois execute **Package Control: Install Package** e procure por
**Santafe**. As próximas versões serão oferecidas pelo próprio Package
Control, sem copiar arquivos manualmente.

## Instalação manual

Se o Package Control não estiver disponível, baixe `Santafe.sublime-package`
e copie-o para o diretório **Installed Packages** aberto por **Preferences →
Browse Packages…** (suba um nível, se necessário). Reinicie o Sublime Text ou
abra esse diretório novamente para ele recarregar o pacote.

Abra um arquivo `.fé`. O seletor de sintaxe, no canto inferior direito, deve
mostrar **Santafé**. As conclusões surgem enquanto você escreve; use
`Ctrl+Espaço` quando quiser chamá-las manualmente.

O sistema de build usa `santafé` e a variante **Verificar sintaxe** usa
`santafec -p`. Portanto o núcleo precisa estar disponível no `PATH` do Sublime
Text.

## Diagnósticos do SLS

Depois de instalar o núcleo Santafé, abra a Paleta de Comandos e execute
**Santafé: Ativar diagnósticos SLS**. A extensão encontra o iniciador instalado,
grava a configuração do servidor e pede ao Package Control o cliente comunitário
**LSP**. Reabra o Sublime Text uma vez para concluir a instalação. Não é preciso
editar preferências nem ajustar o `PATH` gráfico do macOS.

O SLS 0.1.1 diagnostica sintaxe. Conclusões semânticas entre arquivos,
referências, formatação e depuração são evoluções futuras do servidor.

## Catálogo público

Além do repositório oficial do Santafé, a distribuição contém uma exportação
limpa em `dist/github/`, pronta para um repositório público independente e a
submissão posterior ao catálogo geral do Package Control. Essa via elimina até
o único cadastro inicial de repositório para quem usa o catálogo padrão.
