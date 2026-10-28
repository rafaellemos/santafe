# Santafé — candidato dados.8

Revisão privada de dados.7. Não é uma versão estável nem um publicador.
Não altera a Santafé 2.1.0, os editores instalados ou o Pão do Café.

## Contrato aprovado

- Colares brutos: `[=[...]=]`, `[==[...]==]` e níveis com mais `=`.
- A abertura e o fechamento exigem a mesma quantidade de `=` (mínimo um).
- Sem escapes/interpolação. CRLF/CR tornam-se LF; uma quebra inicial após
  a abertura é descartada, como na versão estável. Para preservá-la, use duas.
- Listas `[]`, tabelas `{}`, comentários `--`/`--[[...]]` e suas variantes
  com `=` são preservados. `[[1],[2]]` continua uma lista de listas.
- Um acento grave continua delimitando gabaritos ®/Ⓡ. Dois consecutivos
  significam um gabarito vazio, não texto bruto. ONFÉ rejeita gabaritos.
- Funções continuam com `função ... fim`; nenhuma sintaxe `=>` foi adicionada.
- Listas seguem sem metatabelas. Nulo armazenável e ONFÉ atômico não mudam.

```santafé
local texto = [=[
Texto bruto com ®literal, \n literal e acentos graves: ``.
]=]
local exemplo = [==[Aqui cabe o fechamento ]=] literalmente.]==]
local dados = {texto=texto, itens=[nulo,1], exemplo=exemplo}
local dobro = função(x) retorne x * 2 fim
mostre(dobro(5), dados.texto)
```

## Migração

O migrador `experimentos/dados-v1/migrar.fé` deve rodar com o núcleo estável
2.1.0, sobre fontes estáveis. Converte somente os colares `[[...]]`; conserva
`[=[...]=]` e comentários. Não converte listas/construtores nem atribuições
nulas automaticamente. Escreve o resultado em stdout, sem sobrescrever a entrada.

`experimentos/dados-v8/migrar-candidato.fé` roda com dados.7 sobre fontes desse
candidato e emite JSON com texto transformado/contagem. Preserva o valor dos
brutos, incluindo quebra inicial, escolhe nível sem colisão até nas fronteiras
e não executa o fonte. Não use o lexer estável sobre listas candidatas.

O serializador ONFÉ preserva valores, não delimitadores/comentários originais;
pode escrever colares entre aspas. A ponte JSON mantém quebras e barras pelo
escape apropriado; não interpreta `\n` de um bruto como quebra real.

## Construção e testes locais, sem instalação

Na árvore extraída, conferir o manifesto antes de compilar:

```sh
python3 experimentos/dados-v3/conferir-fontes.py
bash experimentos/dados-v3/construir.sh
make -C ferramentas/sls CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
make -C ferramentas/pacotes CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
python3 experimentos/dados-v7/validar.py
python3 experimentos/dados-v8/testar-fontes.py
python3 experimentos/dados-v8/testar-sls.py
python3 experimentos/dados-v2/editores.py
```

Para comparar migrações, `testar-colares.py` recebe `SANTAFE_ESTAVEL` (binário
2.1.0) e `SANTAFE_DADOS7` (binário anterior). Não omite esses ensaios se faltarem:
é preciso disponibilizar os binários, fora da árvore estável em uso.

Kits gerados: `dist/candidato-dados-v8/editores`. São extensões **0.0.8** de
laboratório, em namespaces separados. Não são atualizações dos catálogos
públicos nem prova de validação visual nativa.

Com Emscripten disponível, `bash experimentos/dados-v7/construir-wasm.sh`
recompila o WASM experimental e executa os casos atualizados de dados.8.
Não reutilizar o WASM de dados.7 com este manual.

Persistência e limites: `experimentos/dados-v7/PERSISTENCIA.md`.
Resultados executados e pendências: `experimentos/dados-v8/RELATORIO.md`.
