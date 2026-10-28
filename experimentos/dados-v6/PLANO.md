# Candidato dados.6 — trabalho isolado

Base imutável: dados.5, SHA-256 8b096db59c22939bdfb306a573ff01b9e6758e70683d7c2f7e94833378bb854f.

Escopo autorizado: migração operacional, manual, carga e visual; nenhum serviço,
banco, catálogo ou editor de produção será atualizado.

1. Preparar gerações completas com manifesto, trava de escritor, ponteiro atômico
   e recuperação após término abrupto; dados persistentes fora das gerações.
2. Migrar o manual na árvore candidata; compilar exemplos e executar as novas
   demonstrações de presença/nulo, listas e colares brutos.
3. Repetir percursos reais e carga concorrente limitada no macOS e Debian;
   registrar latências, RSS, mensagens persistidas e incremental SLS.
4. Conferir apresentação do manual em navegador e os kits experimentais dos
   editores. Inspeção nativa depende de superfície habilitada; não substituir
   teste visual por afirmação baseada em tokenização.
5. Empacotar fontes/evidências com manifesto e checksum; preservar dados.5.

Gates não presumidos: ABI/bytecode definitivos, ONFÉ persistência atômica,
Windows/macOS ARM, migração de dados de negócio, troca real de serviços e carga
prolongada. Ensaiar crash de processo não prova resistência a perda elétrica.

## Fechamento desta rodada

Implementação, correções e baterias concluídas conforme `RELATORIO.md`.
Carga e operação passaram no macOS/Debian. Manual candidato validado nativo e
WASM; corrigido transbordamento móvel. Recortadores dos editores passaram,
mas UI nativa indisponível e não homologada. Entrega final tem checksum externo
e manifesto; produção permanece intacta. Retomar pelos gates enumerados no
relatório, sem repetir como novos os resultados históricos das bibliotecas.
