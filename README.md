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
    local borda = colar.replique("═", tamanho(mensagem) + 2)

    mostre(`╔Ⓡborda╗`)
    mostre(`║ Ⓡmensagem ║`)
    mostre(`╚Ⓡborda╝`)
fim

dêBoasVindas("programador")
```

## Destaques

- Palavras reservadas e funções fundamentais em português;
- Unicode e UTF-8 como parte central da experiência;
- `tamanho` mede grafemas visíveis de colares e segue a mesma medida estrutural de `#` nas tabelas; `octetos` mede bytes de colares para protocolos e dados binários;
- gabaritos literais delimitados por acento grave, com interpolação `Ⓡnome` e `Ⓡ{expressão}`;
- bibliotecas nativas `colar`, `tabela`, `mat`, `es`, `so`, `utf8`, `json`, `corrotina`, `depure` e `módulo`;
- bibliotecas C assíncronas para arquivos, rede/TLS e MariaDB;
- bibliotecas Santafé para imagens, PDF, DNS autoritativo e recursivo, rotas
  web, correio SMTP, telemetria PULSO, operações de 32 ticos e o teste de
  Turing;
- execução nativa em macOS e Linux e uma compilação WebAssembly para o navegador.
- `santafé-sls`, servidor de linguagem local por LSP para diagnósticos de sintaxe
  em tempo real.

## Plataformas

A linha 2.0 tem como plataformas-alvo:

- macOS com Clang;
- Debian GNU/Linux com GCC.

A revisão 2.0.2 passou nas suítes em macOS Intel e Debian, incluindo MariaDB
isolado. VS Code 1.0.6 e Sublime 1.0.13 foram publicados e conferidos nos
editores reais, incluindo HTML/JS concatenados e a paleta suave opcional.
Consulte [o fechamento da versão](docs/LANCAMENTO-2.0.2.md) para distinguir
o pacote aprovado da instalação operacional e conhecer os limites ensaiados.

O fonte conserva pontos de preparação para outras plataformas, mas Windows ainda não faz parte da matriz validada desta versão.

A versão 2.0 altera vocabulário público em relação à 1.0; consulte o
[histórico de alterações](CHANGELOG.md) e o [guia de migração](docs/MIGRACAO-VOCABULARIO-LOGICO.md)
antes de atualizar um projeto.

## Instalação

O instalador detecta o sistema e oferece a instalação das dependências:

```bash
chmod +x instalar.sh
./instalar.sh
```

Com as dependências já presentes, é possível instalar sem privilégios:

```bash
./instalar.sh --sem-dependencias --prefixo "$HOME/.local"
```

Inclua `$HOME/.local/bin` no `PATH`. Para importar bibliotecas dessa instalação
fora de `/usr/local`, configure também `LUA_PATH` e `LUA_CPATH` para os diretórios
`share/santafé/1.0/bibf` e `lib/santafé/1.0/bibc` desse prefixo. O inicializador do
SLS encontra o núcleo e seu fonte pelo próprio prefixo.

As etapas de dependências, compilação e instalação são exibidas no terminal.
Se uma delas parar por rede, confirmação do sistema ou erro de compilação, a
etapa responsável fica visível — o instalador não usa uma animação que esconda
esse diagnóstico.

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

O servidor de linguagem é iniciado pelo editor usando `santafé-sls` em `stdio`.
Ele acompanha a abertura, edição e salvamento dos arquivos e mostra erros de
sintaxe sem executar o programa. As extensões VS Code 1.0.6 e Sublime Text 1.0.13 também oferecem conclusões da API pública, ajuda rápida e navegação local
de funções, mesmo sem depender do SLS. Veja [SLS](docs/SLS.md),
[`extensões/vscode`](extensões/vscode) e [`extensões/sublime`](extensões/sublime).

## Bibliotecas

### Bibliotecas C

- `arquivo`: entrada e saída assíncrona, binária e com gravação atômica durável;
- `rede`: sockets e operações assíncronas sobre GLib/GIO;
- `mariadb`: acesso assíncrono ao MariaDB, consultas preparadas e piscina de conexões;
- `segredo`: aleatoriedade criptograficamente segura e bilhetes;
- `tomada`: conectores TCP, UDP e utilidades de rede.

### Bibliotecas Santafé

- `bit32`;
- `caminheiro`;
- `correio` (cliente, servidor e mensagens SMTP/MIME);
- `nomes` (protocolo DNS, zonas, autoridade e resolvedor iterativo);
- `imagem` (`PNG`, `JPEG` e `SVG`);
- `pulso` (Protocolo Unificado de Leituras, Sinais e Operações);
- `rpdf` (`PDF 2.0`);
- `turing`;
- `vigia` (limites e bloqueios locais da camada de aplicação).

## Documentação

- [Manual completo](https://xn--santaf-gva.dev.br/est%C3%A1tico/manual/)
- [Introdução prática](https://xn--santaf-gva.dev.br/documenta%C3%A7%C3%A3o)
- [Comunidade](https://xn--santaf-gva.dev.br/comunidade)
- [Correio — recepção, distribuição e envios](aplicativos/correio/LEIA-ME.md)
- [Carteiro — caixas e interface web](aplicativos/carteiro/LEIA-ME.md)
- [Correio Santafé](bibs/bibf/correio/LEIA-ME.md)
- [Especificação PULSO/1](bibs/bibf/pulso/LEIA-ME.md)
- [Vigia — proteção local dos serviços](bibs/bibf/vigia/LEIA-ME.md)
- [Nomes — protocolo DNS em Santafé](bibs/bibf/nomes/LEIA-ME.md)
- [Serviços de nomes](aplicativos/nomes/LEIA-ME.md)
- [Arquitetura do ecossistema](docs/ARQUITETURA-DO-ECOSSISTEMA.md)
- [Escalabilidade e implantações externas](docs/ESCALABILIDADE-E-IMPLANTACOES.md)
- [Planejamento do Forte](docs/PLANEJAMENTO-SEGURANCA-E-TELEMETRIA.md)
- [Migração para `lógico` e `_AMBIENTE`](docs/MIGRACAO-VOCABULARIO-LOGICO.md)
- [Auditoria do manual e da API pública](docs/AUDITORIA-MANUAL-2026-10-02.md)
- [SLS — Servidor de Linguagem Santafé](docs/SLS.md)
- [Auditoria 2.0](docs/AUDITORIA-2.0-20261017.md)
- [Lançamento 2.0.2](docs/LANCAMENTO-2.0.2.md)
- [API pública das bibliotecas Fé](docs/API-PUBLICA-DAS-BIBLIOTECAS-FE.md)

## Estrutura

```text
src/       núcleo e biblioteca padrão em C
bibs/bibc/ bibliotecas C opcionais
bibs/bibf/ bibliotecas escritas em Santafé
exemplos/  programas curtos
testes/    verificações do núcleo e das bibliotecas
aplicativos/ aplicações completas construídas com Santafé
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
