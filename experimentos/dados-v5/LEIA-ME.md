# Candidato dados.5 — laboratório de aplicativos e implantação

**Experimental; não instalar em produção.** Não substitui a versão estável.
Pão do Café é projeto separado e não está incluído nesta homologação.

Este pacote contém fontes migradas, testes e manifesto SHA-256. A receita
`preparar.py`, na árvore de desenvolvimento, parte do arquivo dados.4 de hash
fixado e cria outra árvore. `aplicar.py` registra cada correção sem reescrever
os fontes estáveis. Os instaladores públicos e o Makefile da raiz recusam
execução neste candidato: não se pode recompilá-lo acidentalmente sem a ABI
experimental e anunciar uma versão estável. As ferramentas de cópia são
exercitadas exclusivamente pelos ensaios em prefixos temporários próprios.

## Compilar e experimentar o pacote extraído

Dependências já instaladas: compilador C, make, Python 3, GLib/GIO, MariaDB
connector, libsodium e OpenSSL. As baterias de aplicativos/SQL também precisam
de MariaDB server/client/install-db. Não instalam dependências nem pedem sudo.

```sh
python3 experimentos/dados-v3/conferir-fontes.py
sh experimentos/dados-v3/construir.sh
make -C ferramentas/pacotes CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
make -C ferramentas/sls CFLAGS='-O2 -Wall -Wextra -DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK'
sh experimentos/dados-v3/experimentar.sh testes
python3 experimentos/dados-v5/testar-aplicativos.py
python3 experimentos/dados-v5/testar-instalacao.py
```

As baterias criam bancos, prefixos, depósitos e portas altas de loopback.
Geram mensagens fictícias e não consultam DNS público nem entregam e-mail
externo. Logs e snapshots permanecem nos diretórios `/tmp/santafe-*` indicados
ao final. Os processos próprios são encerrados, inclusive após falha.

Para testar atualização/rollback entre candidatos, indique a árvore dados.4
anterior **já compilada na mesma plataforma**, nunca um prefixo operacional:

```sh
python3 experimentos/dados-v5/testar-atualizacao.py /caminho/da/arvore-dados4
```

Esse ensaio faz 4 → 5 → 4 num prefixo novo. Não é homologação de downgrade
da futura versão maior para a versão estável 2.1. O SLS anterior usa apenas
o fechamento/relocação de arquivos corrigido, mantendo núcleo e bibliotecas 4.

Veja `RELATORIO.md` para resultados, limitações e próximos gates. Não há comando
de publicação em produção nem autorização automática para atualizar catálogos.
