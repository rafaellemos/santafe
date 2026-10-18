# Publicação do pacote Santafé para Sublime Text

## Repositório oficial do Santafé

1. Gere os artefatos com `make sublime-repositorio`.
2. Publique `dist/packages.json` e `dist/Santafe-<versão>.sublime-package` em
   `https://xn--santaf-gva.dev.br/est%C3%A1tico/sublime/`.
3. No Sublime Text, o usuário executa uma vez **Package Control: Add
   Repository** com a URL de `packages.json`. Depois instala e atualiza
   **Santafe** pela interface normal do Package Control.

Essa opção não depende de GitHub nem da aprovação do catálogo geral.

## Catálogo público do Package Control

O diretório `dist/github/` é uma raiz de repositório independente: não contém
`package-metadata.json`, pois o Package Control gera esse metadado no processo
de instalação.

Quando a publicação pública for autorizada:

1. crie `github.com/rafaellemos/santafe-sublime`;
2. copie o conteúdo de `dist/github/` para a raiz desse repositório;
3. publique a versão corrente com a tag semântica correspondente (hoje,
   `v1.0.6`);
4. envie uma alteração ao canal oficial do Package Control usando o conteúdo
   de `dist/package-control-entrada.json` como base.

O nome e a URL públicos nessa exportação são uma proposta. Confirme-os antes
de criar o repositório ou a submissão externa.
