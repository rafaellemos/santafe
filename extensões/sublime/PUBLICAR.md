# Publicação do pacote Santafé para Sublime Text

## Repositório HTTPS da Santafé

1. Gere os artefatos com `make sublime-repositorio`.
2. Publique `dist/packages.json` e `dist/Santafe-<versão>.sublime-package` em
   `https://xn--santaf-gva.dev.br/est%C3%A1tico/sublime/`.
3. No Sublime Text, o usuário executa uma vez **Package Control: Add
   Repository** com a URL de `packages.json`. Depois instala e atualiza
   **Santafe** pela interface normal do Package Control.

Essa opção não depende da aprovação do catálogo geral. A versão publicada
no portal é 1.1.0. Não substitua arquivos de uma versão já distribuída.

## Catálogo público do Package Control

O repositório independente é
<https://github.com/rafaellemos/santafe-sublime>. A submissão existente é
<https://github.com/sublimehq/package_control_channel/pull/9622>.
Ela precisa ser aprovada e integrada pelos mantenedores; enviar a atualização
ou obter verificações verdes não equivale a aprovação.

`gerar_repositorio.py` exporta para `dist/github/` somente os arquivos do pacote,
o histórico, a licença MIT da plataforma e os atalhos de preferências de
`catalogo/`. Não exporta `package-metadata.json` (gerado pelo Package Control),
testes, fontes do núcleo nem artefatos de trabalho.

Para sincronizar uma versão:

1. Execute `python3 extensões/sublime/testes/testar_pacote.py` na raiz.
2. Compare os arquivos exportados com o pacote publicado no portal. Na 1.1.0,
   o código permanece idêntico; o README recebe os esclarecimentos finais de
   disponibilidade e requisitos. LICENSE, CHANGELOG e atalhos de preferências
   são os arquivos adicionais da distribuição GitHub. Não reenvie esses bytes
   como substituição do pacote imutável do portal.
3. Sincronize a exportação com o repositório independente, preservando `.git`.
4. Confira o diff, registre um commit e crie a etiqueta `v1.1.0`, somente se
   ela ainda não existir. Nunca mova uma etiqueta de versão publicada.
5. Atualize a entrada existente em `repository/s.json` no ramo da submissão
   com `dist/package-control-entrada.json`. Não abra uma submissão duplicada.
6. Atualize a descrição da submissão e acompanhe suas verificações.

A entrada do catálogo exige **Sublime Text >=4171**, pois o pacote lê recursos
durante a importação do plugin, permitido a partir desse build. O canal central
usa esquema 3.0.0 e não aceita a chave `python_versions`; a seleção do host é
feita pelo arquivo `.python-version` do pacote. O catálogo HTTPS próprio mantém
seu esquema 4.0.0. A restrição é da distribuição pelo catálogo;
não modifica silenciosamente os pacotes já publicados no portal.

O pacote contém uma tecla Enter restrita ao escopo Santafé e complementos de
cores também restritos aos escopos Santafé. Declare esses recursos na revisão,
sem afirmar que não há atalhos nem regras de cores. As preferências e os atalhos
ficam acessíveis pelo menu **Preferences → Package Settings → Santafé** e pela
Paleta de Comandos; a paleta suave de HTML/JS continua opcional.

## Registro do envio 1.1.0 — 21/10/2026

A etiqueta `v1.1.0` do repositório independente aponta para
`d5fc46caa4155c2a64626b73efedcc09fa376dd8`. A submissão #9622 foi atualizada
para essa versão; os workflows `Package test` e `Schema test` ficaram em
`action_required`, aguardando autorização de um mantenedor. Não são testes
aprovados nem aprovação do catálogo. A validação local do pacote e a verificação
de formatação do catálogo passaram.

Errata documental identificada após registrar a etiqueta: a seção final de
diagnósticos ainda descrevia o SLS 0.1.1/0.2 em vez do SLS 1.0.0. O README no
fonte e no ramo `main` independente foi corrigido separadamente; a etiqueta e
os pacotes 1.1.0 foram preservados. Inclua a correção na próxima revisão, sem
mover `v1.1.0` nem substituir o pacote histórico do portal.
