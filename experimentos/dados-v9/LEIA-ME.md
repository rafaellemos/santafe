# Santafé — candidato dados.9

Somente homologação, sem instalação sobre a Santafé 2.1.0. Derivado do pacote
selado dados.8. Mantém listas `[]` (inclusive `[[1],[2]]`), nulo armazenável,
ONFÉ, comentários e colares brutos `[=[...]=]`/`[==[...]==]`. Não exige espaços
entre aberturas de listas e não restaura `[[...]]` como colar.

Esta revisão incorpora a correção de aparência do VS Code: o estilo das
marcações é aplicado por tema claro/escuro para evitar que o renderer 1.142
oculte as cores. Kits experimentais 0.0.9 e SLS 1.0.0-dados.9 identificam esta
entrega; não são versões do Marketplace ou do Package Control.

Após extrair os fontes em diretório privado:

```sh
python3 experimentos/dados-v3/conferir-fontes.py
bash experimentos/dados-v3/construir.sh
make -C ferramentas/sls CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
make -C ferramentas/pacotes CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
python3 experimentos/dados-v2/editores.py
```

A bateria `experimentos/dados-v9/testar.py` exige Node no PATH e os caminhos
`SANTAFE_ESTAVEL` e `SANTAFE_DADOS7` para comparar as migrações. Registra cada
execução e para ao encontrar falhas. Os ensaios de host/pixels são separados.
Não execute `instalar.sh` sobre o sistema. Nenhum publicador de produção
acompanha esta entrega. Leia RELATORIO.md para resultados e limitações.
