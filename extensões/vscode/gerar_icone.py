#!/usr/bin/env python3
"""Gera o PNG do ícone da extensão sem depender de programas gráficos."""

from __future__ import annotations

import pathlib
import struct
import zlib


LADO = 128
SAÍDA = pathlib.Path(__file__).resolve().parent / "icon.png"
PIXELS = bytearray([0, 105, 92, 255] * LADO * LADO)


def pinte(x: int, y: int, cor: tuple[int, int, int, int]) -> None:
    if not (0 <= x < LADO and 0 <= y < LADO):
        return
    início = (y * LADO + x) * 4
    PIXELS[início:início + 4] = bytes(cor)


def retângulo(x0: int, y0: int, x1: int, y1: int, cor: tuple[int, int, int, int]) -> None:
    for y in range(y0, y1):
        for x in range(x0, x1):
            pinte(x, y, cor)


def círculo(cx: int, cy: int, raio: int, cor: tuple[int, int, int, int]) -> None:
    limite = raio * raio
    for y in range(cy - raio, cy + raio + 1):
        for x in range(cx - raio, cx + raio + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= limite:
                pinte(x, y, cor)


def segmento(x0: int, y0: int, x1: int, y1: int, espessura: int, cor: tuple[int, int, int, int]) -> None:
    """Desenha um segmento com pontas circulares."""
    dx, dy = x1 - x0, y1 - y0
    passos = max(abs(dx), abs(dy), 1)
    raio = espessura // 2
    for passo in range(passos + 1):
        x = round(x0 + dx * passo / passos)
        y = round(y0 + dy * passo / passos)
        círculo(x, y, raio, cor)


def trecho(nome: bytes, dados: bytes) -> bytes:
    return struct.pack(
        ">I", len(dados)
    ) + nome + dados + struct.pack(
        ">I", zlib.crc32(nome + dados) & 0xFFFFFFFF
    )


def principal() -> None:
    claro = (178, 223, 219, 255)
    branco = (255, 255, 255, 255)
    dourado = (255, 204, 128, 255)

    # Moldura e o S geométrico mantêm boa leitura em 16 px.
    for x0, y0, x1, y1 in ((12, 12, 116, 16), (12, 112, 116, 116), (12, 12, 16, 116), (112, 12, 116, 116)):
        retângulo(x0, y0, x1, y1, claro)
    segmento(48, 37, 81, 37, 12, branco)
    segmento(46, 38, 46, 62, 12, branco)
    segmento(47, 64, 79, 64, 12, branco)
    segmento(81, 66, 81, 90, 12, branco)
    segmento(48, 92, 80, 92, 12, branco)
    círculo(99, 28, 7, dourado)

    linhas = b"".join(
        b"\x00" + bytes(PIXELS[linha * LADO * 4:(linha + 1) * LADO * 4])
        for linha in range(LADO)
    )
    png = b"\x89PNG\r\n\x1a\n" + trecho(
        b"IHDR", struct.pack(">IIBBBBB", LADO, LADO, 8, 6, 0, 0, 0)
    ) + trecho(b"IDAT", zlib.compress(linhas, 9)) + trecho(b"IEND", b"")
    SAÍDA.write_bytes(png)
    print(SAÍDA)


if __name__ == "__main__":
    principal()
