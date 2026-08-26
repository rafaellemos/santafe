# Santafé

**Pense natural, programe natural.**

Santafé é uma linguagem de programação em português derivada do núcleo do Lua 5.3.6. Ela preserva a leveza e a portabilidade do núcleo original, mas apresenta sintaxe, biblioteca padrão, mensagens e conceitos pensados para falantes do português.

[English version → README.en.md](README.en.md)

## Experimente no navegador

[Abrir o Santafé WebAssembly](https://xn--santaf-gva.dev.br/est%C3%A1tico/wasm/)

## Exemplo

```santafé
local função dêBoasVindas(nome)
    local mensagem = `Bem-vindo, Ⓡnome!`
    local borda = colar.replique("═", utf8.tamanho(mensagem) + 2)

    mostre(`╔Ⓡborda╗`)
    mostre(`║ Ⓡmensagem ║`)
    mostre(`╚Ⓡborda╝`)
fim

dêBoasVindas("programador")
```

## Destaques da versão 1.0.0

- Palavras reservadas e funções fundamentais em português;
- Unicode e UTF-8 como parte central da experiência;
- gabaritos literais delimitados por acento grave, com interpolação `Ⓡnome` e `Ⓡ{expressão}`;
- bibliotecas nativas `colar`, `tabela`, `mat`, `es`, `so`, `utf8`, `json`, `corrotina`, `depure` e `módulo`;
- bibliotecas C assíncronas para rede e MariaDB;
- bibliotecas Santafé para imagens, PDF, rotas web, operações de 32 ticos e o teste de Turing;
- execução nativa em macOS e Linux e uma compilação WebAssembly para o navegador.

## Plataformas

A versão 1.0.0 é validada em:

- macOS com Clang;
- Debian GNU/Linux com GCC.

O fonte conserva pontos de preparação para outras plataformas, mas Windows ainda não faz parte da matriz validada desta versão.

## Instalação

O instalador detecta o sistema e oferece a instalação das dependências:

```bash
chmod +x instalar.sh
./instalar.sh
```

Para apenas compilar, sem instalar:

```bash
make cbin
make cbibc
make test
```

O executável principal é `santafé`:

```bash
santafé exemplos/01-ola.fé
```

## Bibliotecas

### Bibliotecas C

- `rede`: sockets e operações assíncronas sobre GLib/GIO;
- `mariadb`: acesso assíncrono ao MariaDB, consultas preparadas e piscina de conexões;
- `segredo`: aleatoriedade criptograficamente segura e bilhetes;
- `tomada`: conectores TCP, UDP e utilidades de rede.

### Bibliotecas Santafé

- `bit32`;
- `caminheiro`;
- `imagem` (`PNG`, `JPEG` e `SVG`);
- `rpdf` (`PDF 2.0`);
- `turing`.

## Documentação

- [Manual completo](https://xn--santaf-gva.dev.br/est%C3%A1tico/manual/)
- [Introdução prática](https://xn--santaf-gva.dev.br/documenta%C3%A7%C3%A3o)
- [Comunidade](https://xn--santaf-gva.dev.br/comunidade)

## Estrutura

```text
src/       núcleo e biblioteca padrão em C
bibs/bibc/ bibliotecas C opcionais
bibs/bibf/ bibliotecas escritas em Santafé
exemplos/  programas curtos
testes/    verificações do núcleo e das bibliotecas
```

## Desenvolvimento e versões

- `main`: versão estável;
- `desenvolvimento`: próxima versão;
- etiquetas `vX.Y.Z`: versões publicadas e imutáveis.

Veja [CONTRIBUTING.md](CONTRIBUTING.md) antes de propor alterações.

## Licenças

O código próprio do Santafé é distribuído sob a licença MIT. O projeto deriva de Lua e incorpora componentes de terceiros com licenças permissivas. Consulte [TERCEIROS.md](TERCEIROS.md) e os avisos preservados nos respectivos fontes.

## Autor

Rafael Alves Lemos — [santafé.dev.br](https://xn--santaf-gva.dev.br/)
