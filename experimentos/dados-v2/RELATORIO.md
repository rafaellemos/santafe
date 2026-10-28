# Homologação local — candidato dados.2

Data: 23/10/2026. Ambiente: macOS 15.7.7, Intel x86_64. Núcleo: `candidato-dados.2`; SLS: `1.0.0-dados.2`; extensões experimentais: `0.0.2`. Não corresponde a uma publicação de produção.

## Implementação e correções

- O SLS completo roda no mesmo núcleo experimental que analisa listas e colares brutos. Fronteiras JSON usam listas explícitas; caches e documentos usam exclusão explícita, não atribuição de nulo. O auxiliar nativo é vinculado estaticamente com a ABI do candidato.
- ONFÉ recebe diagnósticos do parser de dados, sem executar conteúdo. Também funciona com `languageId=onfe` do Sublime, inclusive buffers sem nome. Provedores de código não renomeiam nem formatam dados ONFÉ.
- `avisosEscopo` é opcional e restrito ao SLS. `local var` e `local var=nulo` são declarações válidas. Não existe `temVar`, nem novo erro de execução para um global ausente. Análise estática não prova a inexistência de globais dinâmicos.
- Corrigida uma leitura de memória já liberada em `depure.lexemas`: a origem longa era duplicada sem ficar ancorada durante coleta de lixo. O lexer agora reutiliza o argumento da pilha. A falha foi reproduzida com AddressSanitizer; o teste de cancelamento original, a regressão específica de nomes longos e a bateria completa passaram depois da correção.
- Kits experimentais preservam os editores estáveis. Realce de listas/brutos, gabaritos Unicode NFC/NFD com `®` e `Ⓡ`, expressões, HTML/JS atravessando concatenações e paleta suave. Marcadores e variáveis interpoladas ficam laranja, sem oblíquo; conteúdo bruto não interpola.

## Ensaios executados

| Ensaio | Resultado |
| --- | --- |
| Núcleo, ONFÉ, JSON, migração e bytecode separado | 10 testes aprovados; inclui 500 valores JSON aleatórios com semente fixa e 3.000 mutações de lista |
| Mesma bateria de núcleo com ASan/UBSan | 10 aprovados |
| SLS experimental, semântica adversarial e transporte/cancelamento | 39 aprovados |
| Mesmos 39 testes SLS com ASan/UBSan | 39 aprovados; detecção de vazamentos desligada, não se declara auditoria de vazamentos |
| Contrato LSP completo no candidato | 39 critérios aprovados |
| Contrato LSP no controle sem dialeto experimental | 39 critérios aprovados |
| Semântica e transporte no núcleo estável | 24 + 5 testes aprovados |
| Gramática/camadas embutidas experimentais | 25 casos aprovados com TextMate/Oniguruma reais |
| Regressão dos realçadores estáveis | 175 casos de gramática, 40 concatenações, recorte Unicode e 3.000 fragmentos aprovados |
| VS Code 1.142.0 real | VSIX instalado em perfil temporário; extensão 0.0.2, SLS 1.0.0-dados.2, definição, rename, símbolos, tokens e erros/correções incrementais de código e ONFÉ aprovados |
| Sublime Text 4215 real com cliente LSP | definição, rename, símbolos, conclusão, tokens e ciclo ONFÉ válido → inválido → corrigido aprovados |

Os totais são por bateria e têm sobreposição; não representam uma soma de testes independentes. O corpus do ecossistema usado pela suíte semântica continua sendo analisado pelo núcleo **estável** de controle: isso não homologa execução das aplicações no novo dialeto.

## Conferência visual

Foram inspecionadas capturas reais dos exemplos públicos nos dois editores: funções, listas, nulo, colares brutos, gabaritos Unicode e HTML/JS em concatenações. Os testes verificaram também os tokens/estilos efetivos. No VS Code, a captura final mostra zero diagnósticos após restaurar os exemplos; os buffers de teste podem continuar marcados como modificados porque a restauração não salva arquivos.

Uma sessão antiga do laboratório Sublime não encaminhou corretamente o diagnóstico ONFÉ; em projeto/sessão novos, a abertura e as mudanças passaram. O ensaio foi ampliado para aguardar o `didOpen` real, testar a mudança incremental e verificar a limpeza do diagnóstico. Nenhuma notificação LSP artificial foi inserida para contornar o cliente. A inspeção visual cobre os exemplos registrados, não todos os temas, plataformas ou combinações de plugins.

Evidências selecionadas acompanham o pacote em `dist/candidato-dados-v2/evidencias`: resultados dos hosts reais, logs de testes e capturas. Não incluem mensagens, credenciais nem arquivos de produção.

## Distribuição e limites

O arquivo local inclui fontes, dois executáveis isolados de candidato/controle, gramáticas, VSIX, pacote Sublime, testes, contrato, relatório e manifesto ONFÉ com SHA-256. Não contém instalador de produção, não muda serviços, não envia arquivos ao servidor e não publica catálogos nem etiquetas.

A extração limpa e a bateria do pacote são verificadas antes da entrega; o registro dessa execução fica junto ao pacote, fora do arquivo compactado para evitar autorreferência de hashes.

Ainda pendentes para uma versão maior: Debian/Windows/WebAssembly, ABI C final, migração das bibliotecas/aplicações, SQL/rede, desempenho/memória de produção, metatabelas em listas, escrita atômica ONFÉ e ponte JSON etiquetada. O suporte SHA-256 embutido desta construção usa CommonCrypto. O candidato é para **homologação local em macOS Intel**, não para substituir Santafé 2.1.0.

Próxima ação: homologar o contrato e o candidato local; só então planejar a migração do ecossistema e a matriz de plataformas. O manual público e a produção permaneceram intactos.
