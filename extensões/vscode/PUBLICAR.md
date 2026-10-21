# Publicação no Visual Studio Marketplace

Identidade da extensão: `santafe.santafe`. A versão do editor é independente da
versão do núcleo. A versão **1.1.0** integra SLS 1.0.0 e gabaritos Unicode,
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
        --out "$area_marketplace/santafe-marketplace-1.1.0.vsix"
)
python3 extensões/vscode/testes/testar_marketplace.py \
    --vsix "$area_marketplace/santafe-marketplace-1.1.0.vsix"
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
em `Verifying`. Esse estado não confirma disponibilidade pública.
SHA-256 do arquivo enviado:
`d80aaea20e1c485077b1ba7342cb3435bb83744ebc28d5dc68096625bb4d6578`.
O runtime e o ícone são idênticos aos do pacote 1.1.0 homologado no portal.
A instalação desse VSIX passou em perfil temporário isolado do VS Code.

Errata documental identificada após o envio: o último parágrafo de SLS ainda
descrevia limitações de uma versão anterior, em contradição com a introdução.
O README no fonte já foi corrigido. O VSIX enviado não foi substituído; leve
esta correção à próxima revisão da extensão, sem reutilizar a versão 1.1.0.
