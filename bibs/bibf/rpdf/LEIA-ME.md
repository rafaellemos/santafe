# RPDF para Santafé

RPDF é a biblioteca Santafé para criar documentos PDF diretamente, sem executar programas externos. Esta versão escreve PDF 2.0 e recebe texto exclusivamente em UTF-8.

## Fonte e Unicode

- A fonte padrão é Noto Sans Regular, incorporada ao PDF.
- O texto das páginas usa fonte composta `Type0`, `CIDFontType2`, `Identity-H`, `CIDToGIDMap` e `ToUnicode`.
- Título, autoria, assunto e demais metadados aceitam UTF-8 e também são gravados em XMP.
- Não existe conversão para ANSI ou Windows-1252.
- Um caractere ausente na fonte produz um erro explícito com seu código Unicode; ele não é substituído silenciosamente.

A fonte Noto Sans é distribuída sob a SIL Open Font License 1.1. A licença acompanha a fonte em `rpdf/fontes/OFL.txt`.

## Exemplo mínimo

```santafé
RPDF = importe "rpdf"

documento = RPDF:novo()
documento:DefinaTítulo("Relatório — Santafé")
documento:AdicionePágina()
documento:DefinaFonte("notoSans", "", 14)
documento:Célula(0, 10, "Ação, coração e comunicação", 0, 1)
documento:Saída("relatório.pdf", "arquivo")
```

## Imagens

`documento:Imagem(...)` incorpora JPEG, PNG e SVG sem chamar programas externos.

- JPEG: aceita fluxos JFIF e Exif, em tons de cinza, RGB ou CMYK, incluindo JPEG progressivo.
- PNG: aceita os cinco tipos de cor do formato, profundidades de 1, 2, 4, 8 e 16 ticos quando permitidas pela especificação, paleta, `tRNS`, canal alfa e entrelaçamento Adam7.
- PNG de 16 ticos por amostra é reduzido para 8 ticos ao entrar no PDF; o RPDF preserva dimensões, cores e transparência, mas não a precisão cromática de 16 ticos.
- SVG permanece vetorial e aceita formas básicas e caminhos M/L/H/V/C/S/Q/T/Z. A primeira versão ainda não aceita arcos, texto, CSS, gradientes, filtros, máscaras, recortes, animação, imagens externas nem transformações.

A biblioteca Santafé `imagem` é instalada junto com o RPDF e pode identificar e ler PNG, JPEG e SVG, além de criar e salvar PNG.

## Instalação

`make ibibf` instala `rpdf.fé`, `imagem.fé` e suas implementações privadas, o leitor TrueType `rpdf_unicode.fé`, a fonte e sua licença. Em uma instalação personalizada, a variável de ambiente `RPDF_FONTE` pode indicar o caminho completo da fonte padrão.

## Limites desta primeira versão Unicode

- Apenas fontes TrueType com contornos TrueType são aceitas pelo leitor atual.
- Noto Sans cobre amplamente textos em português, grego e cirílico, mas não fornece emojis coloridos.
- A fonte completa é incorporada; a redução para somente os glifos usados fica para uma otimização posterior.
- O documento ainda não é marcado estruturalmente para acessibilidade (`Tagged PDF`). O mapa `ToUnicode` já permite copiar e pesquisar o texto corretamente.

## Origem

O RPDF deriva do FPDF de Olivier Plathey e da adaptação para Lua de Domingo Alvarez Duarte. A origem e as licenças de terceiros também estão registradas em `TERCEIROS.md`.
