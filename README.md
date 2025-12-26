# Santafé

*Uma linguagem de programação inspirada em Lua, pensada para ser natural para falantes de português — leve, rápida e embutível.*

## ▶️ Testar no navegador (WASM)

[![Abrir Santafé WASM](https://img.shields.io/badge/Abrir%20no%20Navegador-Santaf%C3%A9%20WASM-2ea44f?style=for-the-badge)](https://xn--santaf-gva.dev.br/estático/wasm)



[English version → README.en.md](README.en.md)

---

## O que é o Santafé?

**Santafé** é uma linguagem/runtime baseada no núcleo do Lua, com foco em:

- **Sintaxe e nomes em português (lusófono-amigável)**
- **Web no DNA** (Já nasce com duas ótimas bibliotecas para desenvolver páginas da internet)
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
```
### Condicionais
```santafe
se idade >= 18 então
  mostre("adulto")
senão
  mostre("menor")
fim
```
### Gabarito literal (crases + Ⓡ{...})
```santafe
nome = "Rafael"
mostre(`Bem-vindo, Ⓡ{nome}!`)
```
---

## Começando
### Compilar do código-fonte (nativo)

#### Requisitos

* Compilador C (GCC/Clang)
* make

#### Construir
```bash
make
```
#### Instalar
```bash
sudo make instalar
```
> Dica: se seu Makefile suportar presets de plataforma (como o Lua), pode existir algo como:
> 
> ```make PLAT=linux```, ```make PLAT=macosx```, etc.


#### Executar
```bash
santafe caminho/do/script.fé
```

## WebAssembly (opcional)
Se você publicar uma build para navegador (por exemplo static/wasm/santafe.wasm + santafe.js), um esqueleto típico é:
```html
<script src="static/wasm/santafe.js"></script>
<script>
  Module.onRuntimeInitialized = () => {
    // ponte JS ↔ runtime (cwrap / funções exportadas)
  };
</script>
```
> A API exata depende das funções exportadas na build WASM (ex.: ```_sf_init```, ```_sf_run_code```, etc.).

## Estrutura do repositório (sugestão)

* ```src/``` — código C do runtime/VM/bibliotecas
* ```include/``` — cabeçalhos
* ```bibf/ or libs/``` — bibliotecas/módulos Santafé
* ```static/wasm/``` — artefatos do navegador (.wasm, JS, assets)
* ```examples/``` — exemplos ```.fé```
* ```docs/``` — documentação
(Ajuste ao seu esquema real.)

## Objetivos / Roteiro
Santafé está sendo concebida com visão de longo-prazo, incluindo:
* Expandir a padronização de nomes em português em toda a base
* Fortalecer bibliotecas padrão e documentação
* Evoluir o runtime web (integração com DOM / SSR / tooling)
* Conteúdo educacional (exemplos → cookbook → referência)
* Experimentos avançados (ex.: redes neurais treinando 100% em Santafé)

## Como contribuir
Contribuições são bem-vindas:

* Abra uma issue com bug/ideia
* Envie PRs pequenos e bem descritos
* Mantenha consistência com o estilo e a nomenclatura do Santafé

## Contato

* Mantenedor: Rafael Lemos
* Página oficial: https://santafé.dev.br -- https://xn--santaf-gva.dev.br
* Discussões/Erros: use GitHub Issues neste repositório

