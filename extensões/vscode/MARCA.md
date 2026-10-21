# Marca da extensão Santafé

Desde a versão 1.0.7, a extensão usa o **cordeiro oficial do portal Santafé**.
O desenho não foi recriado: `icon.svg` é uma cópia exata do arquivo público
[logo_santafé.svg](https://xn--santaf-gva.dev.br/est%C3%A1tico/fotos/logo_santaf%C3%A9.svg),
obtida em 21/10/2026.

SHA-256 do SVG oficial:
`9ce5cab0e3fb7eea923712240e05c68d0fdddad817ed75160220426d43ad82fa`.

O Marketplace recebe `icon.png`, rasterização fiel em **256 × 256 pixels**.
Não há recorte, mudança de cor, novo símbolo ou texto adicionado. O SVG não é
incluído no VSIX, pois o ícone da galeria deve ser PNG.

SHA-256 do PNG aprovado:
`f01ecdbc52c06934e18919a62b0eb4400e7e35be63fbf99e5cc04df47937db6c`.

## Regeneração

Com Node.js e Sharp 0.35.5 disponíveis apenas no ambiente de desenvolvimento:

```sh
python3 gerar_icone.py
```

Se necessário, informe os caminhos com `--node` e `--sharp`. O gerador verifica
o hash do SVG antes de rasterizar e não busca arquivos na rede. O PNG já fica
versionado: nem o usuário nem a instalação da extensão precisam de Sharp.
Variações do rasterizador podem mudar os bytes do PNG; qualquer alteração exige
conferência visual e atualização explícita dos testes e destes hashes.

O antigo gerador de um “S” geométrico foi substituído para evitar que uma nova
compilação recoloque o símbolo incorreto.
