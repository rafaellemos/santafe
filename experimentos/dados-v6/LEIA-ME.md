# Candidato dados.6

Experimental, isolado e sem autorização para instalar em produção.
Leia `RELATORIO.md` antes de interpretar os resultados como liberação estável.

O pacote é source-only, com `MANIFESTO-FONTES.json`. Preserve o checksum externo
de `ENTREGA.md`. Extraia em diretório novo de laboratório. As dependências de
compilação e de MariaDB são as descritas em `experimentos/dados-v5/LEIA-ME.md`;
os testes não instalam dependências e não precisam de sudo.

```sh
python3 experimentos/dados-v3/conferir-fontes.py
sh experimentos/dados-v3/construir.sh
make -C ferramentas/pacotes CFLAGS='-O2 -Wall -fPIC -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
make -C ferramentas/sls CFLAGS='-O2 -Wall -fPIC -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
sh experimentos/dados-v3/experimentar.sh testes
python3 experimentos/dados-v5/testar-aplicativos.py
python3 experimentos/dados-v5/testar-instalacao.py
python3 experimentos/dados-v6/testar-manual.py
python3 experimentos/dados-v6/testar-carga-sls.py
```

O ensaio de aplicativos inclui a carga dados.6 automaticamente; usa portas
altas de loopback e banco próprio. Encerra apenas seus processos. Não envia
e-mail externo e não lê credenciais de produção. Preserva logs em `/tmp`.

Para testar troca/retorno entre gerações, indique apenas o **executável estável
2.1.0**. Ele será lido e copiado para um novo laboratório, nunca instalado ou
alterado. O teste não precisa de acesso a bancos/configurações estáveis.

```sh
python3 experimentos/dados-v6/testar-operacao.py /caminho/do/santafé-2.1.0
```

As receitas `preparar.py` e `manual.py` são geradoras de uma árvore nova; não
devem ser reaplicadas ao manual já transformado. O pacote entregue já contém
o manual candidato. A reconstrução da origem usa a distribuição dados.5 de
hash fixo e a árvore de desenvolvimento, sem sobrescrever aquele arquivo.

O Makefile/instalador público continuam bloqueados no candidato. Não execute
publicadores antigos nem copie esses módulos sobre bibliotecas estáveis.
Não há novo VSIX ou pacote Sublime publicado nesta rodada; os testes dos
recortadores não substituem a inspeção visual nativa pendente.
