# Bateria da cadeia — dados.4, 23/10/2026

Continuar do pacote dados.3, sem refazer o exemplo e sem produção. Preservar
os candidatos anteriores. Nova árvore gerada por `preparar.py` a partir do
arquivo dados.3 com SHA-256 conferido. Alterações semânticas só no laboratório;
suporte C adicional fica protegido pelo modo experimental.

1. Reproduzir falhas do gerenciador: `autores: lista esperada` confirmado no
   primeiro empacotamento com o candidato dados.3 em árvore descartável.
2. Migrar os contratos de listas/objetos, exclusões e compilação C controlada.
   Não relaxar validação de manifestos, caminhos, hashes, lock ou TLS.
3. Repetir empacotamento, instalação, recuperação, CLI, HTTPS e catálogo em
   diretórios temporários; não usar o catálogo público nos testes.
4. Ampliar casos adversariais e injeção de falhas de memória. Executar a mesma
   fonte no Debian. Regressão de bibliotecas, SLS e WebAssembly.
5. Registrar cada resultado e limite. Isso não equivale a homologar toda a
   distribuição, os aplicativos ou UI dos editores.

## Resultado desta rodada

Itens 1–4 concluídos. As dez baterias da cadeia passaram no macOS Intel e no
Debian 12 x86-64. Repetidos em ambos: 76 ensaios de bibliotecas, 12 com banco
temporário, 39 adversariais SLS, 39 de aceitação LSP e a barreira ABI. Núcleo/
ONFÉ: dez testes cruzados no Mac e sete independentes do controle no Debian.
WASM: 16 casos e recuperação após erro. Injeção de falhas nativas e lexer
também repetida com ASan/UBSan no Mac. Detalhes/limites em `RELATORIO.md`.

Árvore ensaiada no Mac: `/tmp/santafe-dados4-m_ueggu6`.
Árvore ensaiada no Debian: `/tmp/santafe-cadeia4.bNaMhCwY/arvore`.
Pacote de fontes usado nos ensaios remotos, antes da documentação final:
`0b5e47ff2c4663d82d5a98add43f33d5d9b439f1078b1887d6a1f48f2032f5a1`.

Uma regressão extra sobre colares multilinha revelou aceitação de controles
crus em JSON e truncamento no NUL. Corrigidos em `lua_cjson.c` sob a opção
experimental. O teste cobre os 32 controles crus/escapados, chaves, valores,
NUL seguido de conteúdo, quebra real e barra-n literal. Todas as baterias
foram repetidas depois dessa correção; o hash acima é da etapa anterior.

Próxima ação: homologar os aplicativos completos e a distribuição/instalação
paralela, sem substituir a versão estável. Não promover dados.4 a estável
somente pelo resultado desta bateria. Não houve nova inspeção visual dos
editores, publicação, push, etiqueta, instalação ou alteração de produção.
