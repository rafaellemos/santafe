# Santafé

*Uma linguagem de programação inspirada em Lua, pensada para ser natural para falantes de português — leve, rápida e embutível.*

> **Status:** em desenvolvimento (WIP). Mudanças podem acontecer com frequência.

[English version → README.en.md](README.en.md)

---

## O que é o Santafé?

**Santafé** é uma linguagem/runtime baseada no núcleo do Lua, com foco em:

- **Sintaxe e nomes em português (lusófono-friendly)**
- **Pegada pequena** (ótimo para scripts, CLI, automação e servidores)
- **Ferramentas práticas** (build nativo e, opcionalmente, WebAssembly para rodar no navegador)

A ideia é manter o espírito do Lua (simplicidade + portabilidade), mas com uma “cara” mais natural em português.

---

## Destaques

- ✅ Runtime em C (rápido e embutível)
- ✅ Palavras-chave e bibliotecas com **nomenclatura em português**
- ✅ **Gabarito literal** com crases + interpolação `®{ ... }`
- ✅ Bom para scripts, automação e criação de bibliotecas
- ✅ Workflow opcional com **WebAssembly** (quando compilado com Emscripten)

---

## Exemplos rápidos

### Olá mundo

```santafe

mostre("Olá do Santafé")
