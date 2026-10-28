# Santafé — candidato dados.7

Somente homologação. Produção, portal, banco empresarial, catálogos, editores
instalados e Git remoto não são alterados. A instalação pública permanece
bloqueada pelos marcadores de laboratório.

Base: pacote imutável dados.6, SHA-256
`ee649d1cce627853e7f561579480e25d2021a835e54c34858bb6d4a7ef8083e6`.

Esta rodada acrescenta persistência atômica ONFÉ, documentação e completude
SLS. Listas continuam sem metatabelas, por decisão de contrato desta versão.
Leia `PERSISTENCIA.md` antes de usar `onfé.grave`/`graveAssíncrono`.

## Construção e testes, somente em árvore privada

Depois de extrair o pacote em diretório temporário próprio:

```sh
python3 experimentos/dados-v3/conferir-fontes.py
bash experimentos/dados-v3/construir.sh
make -C ferramentas/sls CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
make -C ferramentas/pacotes CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
python3 experimentos/dados-v7/validar.py
UBSAN_OPTIONS=halt_on_error=1 python3 experimentos/dados-v7/testar-persistencia.py --sanitizadores
```

O argumento opcional de `validar.py` é o caminho de um núcleo estável 2.1.0:
ativa também o teste de gerações/retorno, copiando esse núcleo para laboratório.
Sem argumento, essa etapa não é executada. Os testes de instalação usam prefixos
privados e não invocam sudo ou instaladores de produção.

Aplicativos completos exigem MariaDB e portas livres de loopback:
`python3 experimentos/dados-v5/testar-aplicativos.py` cria banco, usuários,
certificados e mensagens de ensaio, inicia os próprios processos e os encerra.
Os caminhos antigos `dados-v5/v6` identificam a origem dos harnesses, não o
núcleo executado; as checagens de versão exigem dados.7.

Com emcc e Node disponíveis no PATH, use
`bash experimentos/dados-v7/construir-wasm.sh`. O invólucro exige o marcador
experimental, ativa a opção correta e executa a regressão após compilar.
Não basta chamar emscripten.sh sem a opção: isso constrói o dialeto estável.

O relatório não é autorização para instalar em produção. Próximos gates em
`RELATORIO.md`. O inventário final e os hashes estão em `MANIFESTO-FONTES.json`
e `SHA256SUMS` da entrega, fora da árvore de desenvolvimento estável.
