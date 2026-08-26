# Imagem para Santafé

Biblioteca pura em Santafé para identificar e trabalhar com PNG, JPEG e SVG. A biblioteca pública antiga `png` foi removida; todas as imagens entram por `imagem`.

## API

- `imagem.identifique(fonte [, binário])`: devolve `"png"`, `"jpeg"`, `"svg"` ou `nulo`, examinando o conteúdo.
- `imagem.leia(fonte [, binário])`: lê o arquivo ou colar binário e devolve sua representação.
- `imagem.paraPDF(fonte [, binário])`: produz a representação usada internamente pelo RPDF.
- `imagem.codifique("png", largura, altura, pixels)`: cria um colar binário PNG RGBA.
- `imagem.salve(caminho, "png", largura, altura, pixels)`: codifica e grava um PNG.

```santafé
local imagem = importe "imagem"

imagem.salve("gradiente.png", "png", 320, 180, função(x, y)
    retorne x * 255 // 320, y * 255 // 180, 180, 255
fim)
```

## Formatos

- **PNG:** leitura completa de tons de cinza, RGB, paleta, cinza com alfa e RGBA; profundidades legais de 1 a 16 ticos; `tRNS`, os cinco filtros e Adam7. Valores de 16 ticos por amostra são reduzidos para RGBA de 8 ticos.
- **JPEG:** identifica dimensões, profundidade e espaço de cor; o RPDF incorpora o fluxo comprimido sem recompressão. A primeira versão não transforma JPEG em uma matriz editável de pixels.
- **SVG:** preserva vetores e aceita `svg`, `g`, `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon` e `path`. Caminhos aceitam M, L, H, V, C, S, Q, T e Z; cores podem usar nomes básicos, hexadecimal ou `rgb()`.

O SVG inicial ainda não aceita arcos A, texto, folhas CSS, gradientes, filtros, máscaras, recortes, animação, imagens externas nem transformações no RPDF. Quando algum desses recursos aparece, a biblioteca informa a limitação em vez de produzir silenciosamente uma imagem errada.
