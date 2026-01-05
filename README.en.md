# Santafé

*A Portuguese-friendly programming language inspired by Lua — designed to feel natural for Portuguese speakers while staying lightweight, fast, and embeddable.*

> **Status:** Work in progress / evolving project. Expect changes as the language and standard library grow.
## ▶️ Test in browser (WASM)

[![Open Santafé WASM](https://img.shields.io/badge/Open%20in%20Browser-Santaf%C3%A9%20WASM-2ea44f?style=for-the-badge)](https://xn--santaf-gva.dev.br/estático/wasm)

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
- ✅ **Template literals** with backticks and interpolation using `®{ ... }`
- ✅ Works well for scripting, automation, and building higher-level libraries
- ✅ Optional **WebAssembly** workflow for running in the browser (when built with Emscripten)

---

## Quick taste

### Hello world

```santafe
mostre("Hello from Santafé")
```
### Conditionals
```santafe
se idade >= 18 então
  mostre("adulto")
senão
  mostre("menor")
fim
```
### Template literal (backticks + Ⓡ{...})
```santafe
nome = "Rafael"
mostrar(`Bem-vindo, Ⓡ{nome}!`)
```
---

## Getting started
### Build from source (native)

#### Requirements

* A C toolchain (GCC/Clang)
* make

#### Build
```bash
make
```
#### Install
```bash
sudo make install
```
> Tip: If your Makefile supports platform presets (like Lua’s), you may be able to use:
> 
> make PLAT=linux, make PLAT=macosx, etc.


#### Run
```bash
santafe path/script.fé
```

## WebAssembly (optional)
If you ship a browser build (e.g. static/wasm/santafe.wasm + santafe.js), a typical integration looks like:
```html
<script src="static/wasm/santafe.js"></script>
<script>
  // Example: call into the runtime once Module is ready
  Module.onRuntimeInitialized = () => {
    // your bridge code here (cwrap / exported functions)
  };
</script>
```
> The exact API depends on what you export in your WASM build (e.g. _sf_init, _sf_run_code, etc.).

## Project layout (suggested)
Typical folders you might have in this repo:
* ```src/``` — C source (runtime / VM / libraries)
* ```include/``` — headers
* ```bibf/ or libs/``` — Santafé libraries/modules
* ```static/wasm/``` — browser build artifacts (.wasm, JS glue, assets)
* ```examples/``` — Santafé examples (.fé)
* ```docs/``` — documentation

## Goals / Roadmap
Santafé is built with a long-term vision, including:
* Expand “Portuguese-native” naming across the whole ecosystem
* Improve the standard library surface (consistent modules and docs)
* Strengthen the web runtime (DOM integration / SSR helpers, tooling)
* Build higher-level educational content (examples → cookbook → reference)
* Enable advanced experimentation (e.g., neural networks training fully in Santafé)

## Contributing
Contributions are welcome!
* Open an issue to discuss ideas/bugs
* Send a PR with clear description and test notes
* Keep changes focused and consistent with Santafé’s naming/style goals

## Contact

* Maintainer: Rafael Lemos
* Project website: https://santafé.dev.br -- https://xn--santaf-gva.dev.br
* Discussion/Issues: use GitHub Issues in this repository
