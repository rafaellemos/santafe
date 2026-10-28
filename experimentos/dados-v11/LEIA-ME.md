# Santafé dados.11 — somente homologação

Não instalar em produção. Este candidato não substitui a versão estável.
Leia RELATORIO.md e ESTADO.json antes de interpretar os testes.

`preparar.py` deriva a árvore dos fontes selados dados.10; `empacotar.py`
produz o arquivo determinístico com manifesto SHA-256. O núcleo mantém IBA3.

O roteiro da réplica exige Linux, a captura privada e uma restauração íntegra
do próprio servidor. `migrar-replica.py` cria gerações privadas em `/var/tmp`,
isola rede/montagens/PIDs e compara estável, candidata e rollback. Recusa espaço
insuficiente e não lê bancos de produção: usa somente o dump já capturado.
Não executar o coletor nem o ensaio como forma de publicar esta versão.

Os relatórios exportáveis têm somente contagens e resultados. Logs completos,
configurações, SQL e conteúdo postal ficam privados no servidor. O ensaio usa
certificados e credenciais locais de teste, nunca o relay externo.

Para conferir a entrega, execute `sha256sum -c SHA256SUMS` dentro dela.
Não há comando `sudo` de publicação nesta revisão.
