# Santafé

**Think naturally, program naturally.**

Santafé is a Portuguese programming language derived from the Lua 5.3.6 core. It keeps the small, portable runtime while presenting syntax, standard libraries, diagnostics, and concepts designed for Portuguese speakers.

[Versão em português → README.md](README.md)

## Try it in the browser

[Open the Santafé WebAssembly playground](https://xn--santaf-gva.dev.br/est%C3%A1tico/wasm/)

## Supported platforms

Version 1.0.0 is validated on macOS with Clang and Debian GNU/Linux with GCC. Windows is not part of the validated 1.0.0 matrix yet.

## Install

The installer detects the environment and offers to install the required dependencies:

```bash
chmod +x instalar.sh
./instalar.sh
```

Compile without installing:

```bash
make cbin
make cbibc
make test
```

Run an example:

```bash
santafé exemplos/01-ola.fé
```

## Documentation

- [Full manual](https://xn--santaf-gva.dev.br/est%C3%A1tico/manual/)
- [Practical introduction](https://xn--santaf-gva.dev.br/documenta%C3%A7%C3%A3o)
- [Community](https://xn--santaf-gva.dev.br/comunidade)

## Repository layout

```text
src/       C runtime and standard library
bibs/bibc/ optional C libraries
bibs/bibf/ libraries written in Santafé
exemplos/  short programs
testes/    runtime and library checks
```

## Branches and releases

- `main`: stable line;
- `desenvolvimento`: next version;
- `vX.Y.Z` tags: immutable published releases.

## Licensing

Original Santafé code is released under the MIT License. The project derives from Lua and incorporates permissively licensed third-party components. See [TERCEIROS.md](TERCEIROS.md) and the notices retained in the source files.

## Author

Rafael Alves Lemos — [santafé.dev.br](https://xn--santaf-gva.dev.br/)
