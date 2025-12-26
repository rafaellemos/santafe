# Santafé

*A Portuguese-friendly programming language inspired by Lua — designed to feel natural for Portuguese speakers while staying lightweight, fast, and embeddable.*

> **Status:** Work in progress / evolving project. Expect changes as the language and standard library grow.

---

## What is Santafé?

**Santafé** is a Lua-based language/runtime that focuses on:

- **Portuguese-first syntax and naming**
- **Small footprint** (great for CLI tools, embedded scripting, and servers)
- **Practical tooling** (native build, and optional WebAssembly builds for the browser)

Santafé aims to keep the spirit of Lua (simplicity + portability) while making the surface language more welcoming to Portuguese speakers.

---

## Highlights

- ✅ Lua-inspired runtime in C (fast, embeddable)
- ✅ Portuguese keywords and a more “local” standard library naming style
- ✅ **Template literals** with backticks and interpolation using `Ⓡ{ ... }`
- ✅ Works well for scripting, web, automation, and building higher-level libraries
- ✅ Optional **WebAssembly** workflow for running in the browser (when built with Emscripten)

---

## Quick taste

### Hello world

```santafe

mostre("Olá do Santafé")
