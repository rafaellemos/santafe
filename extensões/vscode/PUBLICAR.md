# Publicação no Visual Studio Marketplace

Identidade da extensão: `santafe.santafe`. A versão do editor é independente da
versão do núcleo. A versão **1.1.1** corrige o README da 1.1.0, que integra
SLS 1.0.0 e gabaritos Unicode,
preservando o cordeiro oficial introduzido em 1.0.7. A marca e sua origem estão
registradas em [MARCA.md](MARCA.md).

## Preparar e validar

O `empacotar.py` mantém o VSIX determinístico de instalação manual. Não substitua
um download já publicado por bytes diferentes sob a mesma versão/URL.

Para a galeria, use `preparar_marketplace.py`: ele exporta somente a lista pública
de arquivos, acrescenta a licença MIT do projeto e os metadados de repositório,
suporte e página oficial. A pasta de destino deve ser nova. Não copie uma árvore
de desenvolvimento inteira nem arquivos de credenciais para essa pasta.

Na raiz do repositório, com Python 3, Node 22+ e o empacotador oficial
`@vscode/vsce` **4.0.0** disponíveis:

```sh
python3 extensões/vscode/testes/testar_marketplace.py
area_marketplace=$(mktemp -d)
python3 extensões/vscode/preparar_marketplace.py "$area_marketplace/extensao"
(
    cd "$area_marketplace/extensao"
    vsce package --no-dependencies --githubBranch desenvolvimento \
        --out "$area_marketplace/santafe-marketplace-1.1.1.vsix"
)
python3 extensões/vscode/testes/testar_marketplace.py \
    --vsix "$area_marketplace/santafe-marketplace-1.1.1.vsix"
```

`--no-dependencies` é intencional: os runtimes TextMate/Oniguruma e suas licenças
já fazem parte da lista explícita. O pacote não exige `npm install` do usuário.
Não use opções para ignorar a licença, a detecção de segredos ou erros do vsce.

O teste compara o código empacotado byte a byte com os fontes da versão, confere
a identidade e exige os ativos de README, licença e ícone no manifesto da
galeria. O vsce pode normalizar nomes/links do README e gerar seu próprio
manifesto; o VSIX da galeria, portanto, não tem o mesmo hash do VSIX manual.

## Enviar e conferir

1. Entre na [gerência do Marketplace](https://marketplace.visualstudio.com/manage).
2. Confirme o publicador `santafe`. A criação de um novo publicador exige que o
   titular aceite o contrato; o identificador não pode ser alterado depois.
3. Na primeira publicação, use **New extension → Visual Studio Code**; para uma
   revisão, use **More Actions → Update**. Envie o VSIX validado. A interface
   autenticada permite publicar sem criar nem armazenar um PAT.
4. Aguarde a validação da Microsoft. Upload aceito não significa publicação
   concluída. Confira o estado na gerência e a versão na página pública:
   `https://marketplace.visualstudio.com/items?itemName=santafe.santafe`.
5. Só anuncie a instalação pelo catálogo após a versão estar disponível. Teste
   `code --install-extension santafe.santafe` em perfil isolado; não substitua
   silenciosamente a extensão instalada no ambiente de trabalho do usuário.

O SLS continua local e depende da instalação do núcleo Santafé. Nenhum processo
postal ou do portal precisa ser reiniciado para publicar uma extensão.

Referência: [publicação oficial de extensões](https://code.visualstudio.com/api/working-with-extensions/publishing-extension).

## Registro do envio 1.1.0 — 21/10/2026

O VSIX gerado pelo vsce 4.0.0 foi aceito pela gerência do Marketplace e entrou
em `Verifying`. Depois, a Microsoft liberou a 1.1.0: a gerência deixou de
mostrar a verificação pendente e o histórico público passou a listar 1.1.0.
SHA-256 do arquivo enviado:
`d80aaea20e1c485077b1ba7342cb3435bb83744ebc28d5dc68096625bb4d6578`.
O runtime e o ícone são idênticos aos do pacote 1.1.0 homologado no portal.
A instalação desse VSIX passou em perfil temporário isolado do VS Code.
A instalação diretamente da galeria, em outro perfil temporário, também passou:
`code --install-extension santafe.santafe@1.1.0`. A listagem retornou
`santafe.santafe@1.1.0`; as extensões pessoais do usuário não foram alteradas.

Errata documental identificada após o envio: o último parágrafo de SLS ainda
descrevia limitações de uma versão anterior, em contradição com a introdução.
O README no fonte foi corrigido. O VSIX 1.1.0 não foi substituído; a correção
foi incorporada à revisão 1.1.1 descrita abaixo.

## Registro do envio 1.1.1 — 21/10/2026

Revisão documental, sem alteração de runtime, ícone ou configurações. O VSIX
oficial contém o README corrigido; os testes conferem explicitamente essa
descrição dentro do arquivo enviado. A comparação com a 1.1.0 permite somente
README, versão no manifesto e manifesto VSIX diferentes.

SHA-256 enviado:
`352943c6b00d15cd201639db70da1763fd62a8598761a5d9ae3e79b07d709b06`.
Testes de estrutura, metadados, conclusões, integração do cliente SLS,
gabaritos e concatenações passaram. A instalação do VSIX em perfil temporário
isolado retornou `santafe.santafe@1.1.1`, sem alterar as extensões pessoais.
Após a verificação da Microsoft, a gerência passou a mostrar 1.1.1 pública
e o histórico da página pública confirmou a versão. O README público contém
a descrição atual do SLS 1.0.0. A instalação diretamente da galeria, em outro
perfil temporário isolado, também passou:
`code --install-extension santafe.santafe@1.1.1`. A listagem confirmou
`santafe.santafe@1.1.1`, e o README instalado contém a correção documental.

Os downloads 1.1.0 do portal e as etiquetas do núcleo permanecem inalterados.

Na primeira execução de CI desta revisão, o ensaio conjunto ainda procurava
os editores 1.1.0 da entrega 2.1.0. O manifesto de preparação do fonte agora
identifica os editores 1.1.1 e fica explicitamente **não homologado para uma
nova entrega conjunta**. As evidências da 2.1.0 e sua etiqueta não mudaram.
Não republique núcleo ou distribuição histórica com esse manifesto.

O verificador operacional e sua execução original no workflow foram
preservados. Oito testes adicionais exercitam aceitação dos metadados
históricos e recusa de versões divergentes, evidências ausentes e gates
pendentes. O pré-voo verifica coerência, mas a validação final do conjunto
continua recusando o fonte até haver identidade e homologação próprias para
outra entrega conjunta. A publicação independente dos editores não exige
reinstalar o núcleo nem alterar o servidor.

No commit `65db9180d90b077792772f3c353635cef0822e33`, as quatro tarefas
automáticas passaram em Ubuntu 24.04 e macOS 14:
[núcleo, manual e editores](https://github.com/rafaellemos/santafe/actions/runs/39598962372)
e [SLS e bibliotecas](https://github.com/rafaellemos/santafe/actions/runs/39598962271).
Isso não equivale à aprovação da submissão do Sublime no Package Control,
que continua dependendo dos mantenedores daquele catálogo.
