# Runtime do realce embutido

Componentes distribuídos com o VSIX, sem instalação npm nem acesso à rede:

- `vscode-textmate` 9.3.2, MIT: https://github.com/microsoft/vscode-textmate
- `vscode-oniguruma` 1.7.0, MIT e avisos das dependências:
  https://github.com/microsoft/vscode-oniguruma

Os arquivos de runtime foram copiados sem alterações da instalação do VS Code
em 18/10/2026. As licenças e avisos originais estão preservados. Nenhum script
de instalação desses pacotes é executado; somente JS e WebAssembly locais.
As gramáticas HTML, JavaScript e CSS são lidas das contribuições públicas das
extensões nativas do editor, não copiadas nem buscadas no projeto aberto.

A API pública `DocumentSemanticTokensProvider` aplica as cores sobre os trechos
literais. Isso é realce léxico, não análise semântica HTML/JS nem execução SLS.
O empacotador fixa datas/permissões e verifica reprodutibilidade byte a byte.
