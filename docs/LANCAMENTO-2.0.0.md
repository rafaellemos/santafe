# Santafé 2.0.0

Santafé 2.0.0 é o primeiro lançamento estável da linha 2. Ele é validado em
macOS com Clang e em Debian GNU/Linux com GCC. Windows ainda não integra a
matriz de plataformas homologadas.

## Distribuição

O pacote fonte contém o núcleo, as bibliotecas, o SLS, a documentação, os
testes e as extensões de editor. Há dois artefatos de editor distribuídos
separadamente:

- `santafe-vscode-1.0.0.vsix`, para **Extensions: Install from VSIX…** no VS
  Code;
- `Santafe.sublime-package`, para o diretório **Installed Packages** do Sublime
  Text 4.

Os dois reconhecem `.fé` e `.fe`, oferecem realce, snippets, conclusões da API
pública e ajuda local. O VS Code inicia o SLS automaticamente; no Sublime, os
diagnósticos requerem o cliente comunitário LSP e a configuração de exemplo
incluída no pacote.

## Migração da 1.0

Leia [MIGRACAO-VOCABULARIO-LOGICO.md](MIGRACAO-VOCABULARIO-LOGICO.md) antes de
atualizar. Os pontos incompatíveis são o nome do tipo `lógico`, o ambiente
léxico `_AMBIENTE` e a contagem de grafemas por `tamanho` em colares.

## Escopo conhecido

O SLS 0.1.0 é propositalmente sintático: ele não executa o documento e não
oferece, ainda, inferência de tipos, análise de importações entre arquivos,
referências globais, formatação ou depuração. Essas são próximas evoluções,
não funcionalidades anunciadas como presentes nesta versão.
