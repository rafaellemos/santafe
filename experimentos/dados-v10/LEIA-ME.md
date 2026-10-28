# Santafé — candidato dados.10

Pacote de homologação: **não instalar em produção**. Não há publicador estável,
tag, push, atualização do portal nem alteração dos catálogos dos editores.

Esta revisão define IBA 3, recompila os módulos nativos, separa o bytecode e
prepara a captura/restauração privada da instalação. Mantém o contrato dados.9:
listas `[]`, nulo armazenável, ONFÉ, SLS e colares brutos `[=[...]=]`/níveis com
mais `=`; gabaritos com um acento grave e comentários `--`/`--[[...]]`.

A entrega contém fontes com manifesto SHA-256, manual candidato, kits separados
0.0.10, executor WebAssembly e evidências. O núcleo ensaiado e o SLS identificam
`dados.10`/`1.0.0-dados.10`. A sintaxe e a paleta dos editores não foram alteradas
em relação ao candidato9; não se declara nova inspeção visual dos kits10.

Leia `RELATORIO.md`, `IBA.md` e `MIGRACAO.md` antes de homologar. A migração da
réplica real e os demais gates de promoção não se tornam aprovados por haver
uma rodada de testes sintéticos aprovada.

No servidor, conferir a entrega não instala nada:

```sh
cd /tmp/santafe-dados10.v901wuit/entrega
sha256sum -c SHA256SUMS
```

A captura operacional requer a senha sudo do operador, sem transmiti-la:

```sh
sudo python3 /tmp/capturar-replica-dados10.py --copiar-dados
```

Informe depois o caminho `REPLICA_CAPTURADA`. A cópia é privada, contém dados e
credenciais e deve permanecer no servidor. Ela não integra este pacote.
Nenhum aplicativo pode ser iniciado a partir da cópia antes da adaptação de
caminhos/destinos e isolamento descritos em `MIGRACAO.md`.
