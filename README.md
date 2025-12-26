# Santafé

*Uma linguagem de programação inspirada em Lua, pensada para ser natural para falantes de português — leve, rápida e embutível.*

> **Status:** em desenvolvimento (WIP). Mudanças podem acontecer com frequência.

[English version → README.en.md](README.en.md)

---

## O que é o Santafé?

**Santafé** é uma linguagem/runtime baseada no núcleo do Lua, com foco em:

- **Sintaxe e nomes em português (lusófono-friendly)**
- **Web no DNA** (Já nasce com duas ótimas biblitecas para desenvolver páginas da internet)
- **Ferramentas práticas** (build nativo e, opcionalmente, WebAssembly para rodar no navegador)

A ideia é manter o espírito do Lua (simplicidade + portabilidade), mas com uma “cara” mais natural em português.
Também adicionar ferramentas e bibliotecas úteis para o programador.

---

## Destaques

- ✅ Runtime em C (rápido e embutível)
- ✅ Palavras-chave e bibliotecas com **nomenclatura em português**
- ✅ **Gabarito literal** com crases + interpolação `Ⓡ{ ... }`
- ✅ Bom para scripts, automação e criação de bibliotecas
- ✅ Workflow opcional com **WebAssembly** (quando compilado com Emscripten)
- ✅**Web** (Duas ótimas biblitecas para desenvolver páginas da internet)
- ✅**Assíncrono** (Já suporta servidores web com alta carga **piscina+fila de conexões**)
---

## Exemplos rápidos

### Olá mundo

```santafe

mostre("Olá do Santafé")
