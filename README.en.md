# Santafé

**Think naturally, program naturally.**

Santafé is a Portuguese programming language derived from the Lua 5.3.6 core. It keeps the small, portable runtime while presenting syntax, standard libraries, diagnostics, and concepts designed for Portuguese speakers.

The development line also includes an asynchronous SMTP client/server named
`correio` and **PULSO/1** (Unified Protocol for Readings, Signals and
Operations), the local telemetry foundation planned for the future Forte.

[Versão em português → README.md](README.md)

## Try it in the browser

[Open the Santafé WebAssembly playground](https://xn--santaf-gva.dev.br/est%C3%A1tico/wasm/)

## Supported platforms

The 2.0 line targets macOS with Clang and Debian GNU/Linux with GCC.
Candidate 2.0.2 has been revalidated locally on macOS; this audit's Linux run
and remote publication remain pending. Windows is not part of the validated matrix yet.

Version 2.0 changes public vocabulary relative to 1.0; read the
[change log](CHANGELOG.md) and the [migration guide](docs/MIGRACAO-VOCABULARIO-LOGICO.md)
before upgrading a project.

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

Editors start the local language server through `santafé-sls` over standard
input/output. It reports syntax diagnostics on open, edit, and save without
executing the edited program. The VS Code and Sublime Text extensions also
offer public-API completion, hover help, and local function navigation without
depending on the SLS. See [SLS](docs/SLS.md).

## Libraries

The optional C libraries include asynchronous durable file operations
(`arquivo`), networking/TLS (`rede` and `tomada`), MariaDB access,
prepared statements and connection pooling (`mariadb`), and cryptographic
randomness (`segredo`). Libraries written in Santafé provide web routing,
SMTP/MIME mail, the `nomes` authoritative and recursive DNS library, images,
PDF 2.0, PULSO telemetry, local application-layer protection with `vigia`,
32-bit operations, and the Turing test.

For text, `tamanho` counts user-perceived grapheme clusters; for tables, it
uses the same structural sequence measure as `#` and does not count every key
in a sparse map. `octetos` measures stored bytes in strings, which is
appropriate for binary data and wire protocols. The `#` operator retains its
native structural meaning for both strings and tables.

## Documentation

- [Full manual](https://xn--santaf-gva.dev.br/est%C3%A1tico/manual/)
- [Practical introduction](https://xn--santaf-gva.dev.br/documenta%C3%A7%C3%A3o)
- [Community](https://xn--santaf-gva.dev.br/comunidade)
- [Correio mail services (Portuguese)](aplicativos/correio/LEIA-ME.md)
- [Carteiro mailbox and web interface (Portuguese)](aplicativos/carteiro/LEIA-ME.md)
- [Correio Santafé reference (Portuguese)](bibs/bibf/correio/LEIA-ME.md)
- [PULSO/1 specification (Portuguese)](bibs/bibf/pulso/LEIA-ME.md)
- [Vigia local protection library (Portuguese)](bibs/bibf/vigia/LEIA-ME.md)
- [Nomes DNS library (Portuguese)](bibs/bibf/nomes/LEIA-ME.md)
- [Nomes services (Portuguese)](aplicativos/nomes/LEIA-ME.md)
- [Ecosystem architecture (Portuguese)](docs/ARQUITETURA-DO-ECOSSISTEMA.md)
- [SLS language server](docs/SLS.md)
- [2.0.1 release](docs/LANCAMENTO-2.0.1.md)

## Repository layout

```text
src/       C runtime and standard library
bibs/bibc/ optional C libraries
bibs/bibf/ libraries written in Santafé
exemplos/  short programs
testes/    runtime and library checks
aplicativos/ complete applications built with Santafé
```

## Branches and releases

- `main`: stable line;
- `desenvolvimento`: next version;
- `vX.Y.Z` tags: immutable published releases.

## Licensing

Original Santafé code is released under the MIT License. The project derives from Lua and incorporates permissively licensed third-party components. See [TERCEIROS.md](TERCEIROS.md) and the notices retained in the source files.

## Author

Rafael Alves Lemos — [santafé.dev.br](https://xn--santaf-gva.dev.br/)
