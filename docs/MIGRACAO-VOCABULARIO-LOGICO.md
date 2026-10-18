# Migração do vocabulário: `lógico` e `_AMBIENTE`

## Situação

A versão 2.0.0 do Santafé adota `lógico` como nome público do tipo de
`verdadeiro` e `falso` e `_AMBIENTE` como nome especial do ambiente léxico.
Essas duas mudanças são incompatíveis no nível do fonte com a versão
1.0.0.

A ABI C permanece identificada por `LUA_VERSION_NUM == 503`, pois deriva do
núcleo Lua 5.3. Esse número identifica o contrato binário da API C e não a
versão, a sintaxe ou o vocabulário público do Santafé. Na linha 2.0 os
diretórios `santafé/1.0` continuam sendo o layout de instalação, não o número
do lançamento. O formato de bytecode também não mudou; isso não torna
programas antigos semanticamente compatíveis. Recompile os fontes após migrar.

Outras mudanças incompatíveis: `tamanho`/`colar.tamanho` contam grafemas em
vez de bytes; nomes legados como `tabela.maiorN` foram removidos (use
`tabela.maiorÍndice`); `colar.descompacte` tem limite padrão de saída de
64 MiB. Consulte os limites e o custo das operações no manual.

## Tipo lógico

Antes:

```santafé
garanta(tipo(verdadeiro) == "booleano")
```

Agora:

```santafé
garanta(tipo(verdadeiro) == "lógico")
garanta(tipo(falso) == "lógico")
```

Devem ser revistas comparações com o resultado textual de `tipo`, tabelas de
despacho por nome de tipo, validadores, serializadores e mensagens de erro.
Os valores `verdadeiro` e `falso` e sua representação interna não mudaram.

## Ambiente léxico

Antes:

```santafé
local _ENV = ambienteControlado
```

Agora:

```santafé
local _AMBIENTE = ambienteControlado
```

`_AMBIENTE` é o nome reconhecido pelo compilador para resolver e definir
nomes não locais. `_G` continua apontando para a tabela global original.

O nome `_ENV` não é reservado e não possui comportamento especial. Ele pode
ser usado como uma variável comum:

```santafé
local _ENV = "nome comum"
garanta(_ENV == "nome comum")
```

Não há apelido de compatibilidade. Essa decisão impede dois nomes públicos
para o mesmo conceito e torna erros de migração visíveis.

## O que não deve ser traduzido mecanicamente

- `LUA_VERSION_NUM`, `lua_toboolean`, `lua_pushboolean` e nomes semelhantes
  pertencem à API C compatível com Lua;
- `gboolean` pertence à API do GLib;
- `BOOLEAN`, `TRUE` e `FALSE` em esquemas SQL pertencem ao dialeto do banco;
- `boolean` em JavaScript, Python, JSON normativo ou bibliotecas externas é
  terminologia do sistema integrado, não do vocabulário Santafé;
- distribuições históricas imutáveis devem preservar o comportamento da
  versão publicada.

## Verificação

Compile o núcleo e execute a suíte:

```bash
make cbin
make cbibc
make test
```

O teste `testes/integracao/testar_vocabulario_publico.sh` verifica o
interpretador nativo, o manual e, quando presente, o executor WebAssembly.

## Fechamento da migração

Em 2 de outubro de 2026 foram validados:

- o interpretador nativo, devolvendo `lógico` para os dois valores lógicos;
- o ambiente léxico especial `_AMBIENTE`;
- o executor WebAssembly usado pelo manual, sem as cadeias `booleano` e
  `_ENV`;
- o PULSO/1, preservando valores lógicos;
- o manual completo, com 1.216 identificadores, 562 funções colapsáveis e
  172 exemplos executáveis;
- a suíte local completa do projeto;
- os serviços Nomes, portal, Correio, IMAP e Carteiro em execução no Linux.

As menções restantes a `_ENV` no manual e no teste são intencionais: elas
documentam e comprovam que o nome antigo deixou de ter significado especial.
