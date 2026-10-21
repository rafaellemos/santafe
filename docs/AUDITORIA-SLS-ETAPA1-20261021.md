# SLS — análise precisa e sincronização incremental

Data: 21/10/2026. macOS 15.7.7 Intel, Python 3.9.6, Node 24.19.0.
Base Git: `aba35374154a0cdc5ecc4d55a3fbdf327f7f3355`, árvore modificada.
Identidade do servidor testado: **0.2.0-dev.1**, ainda não publicado.

## Implementação

- Intervalos de tokens no lexer/parser real, inclusive lookahead, literais
  incompletos, EOF e erros adiados de `pare`/`vápara`.
- API C aditiva `lua_loaddiagnostic` e `depure.analise`, sem executar o fonte ou
  suas importações e sem mudar os retornos de `carregue`.
- Conversão octetos → UTF-16, incluindo emoji, marcas combinantes e CRLF/CR.
- Lotes incrementais sequenciais e atômicos, versões monotônicas, substituição
  integral, fechamento/reabertura e limites de tamanho/trabalho.
- Rejeição explícita de lotes inválidos, limpeza de diagnósticos obsoletos e
  ressincronização por texto integral/reabertura. Sem alegar recuperação
  automática que LSP não define.
- Manual, contrato, catálogo compartilhado dos editores e testes atualizados.
  Fixtures da bateria-alvo passaram a usar crases nos gabaritos reais, em vez
  de aspas comuns, e a anotação reconhecida `--[[javascript]]`.

## Evidências locais

| Ensaio | Resultado |
| --- | --- |
| `make cbin` e teste Fé do analisador | Aprovados |
| Consumidor C da API | Fragmentação em todos os tamanhos do fixture, UTF-8 dividido, lookahead, leitores reentrantes, pilha e limpeza de diagnóstico aprovados |
| Sincronização incremental | 24 testes aprovados; inclui 100 edições aleatórias determinísticas comparadas com outro processo que recebe texto integral |
| Protocolo e robustez anteriores | Aprovados |
| Verificador independente | 17 testes aprovados |
| Perfil atual | 13 OK, zero falhas |
| Contrato-alvo 1.0 | **15 OK, zero falhas, 24 pendências**; saída 2 esperada |
| `testar.sh` | Código zero; 84 arquivos de testes chamados, além das verificações de integração |
| Manual | 1.238 IDs, 581 funções colapsáveis, 171 exemplos, 259 contratos C e 344 Fé |
| Instalação temporária com espaços | Núcleo, bibliotecas, PDF, launcher e handshake aprovados; 13 critérios base e os 2 novos critérios do alvo aprovados pelo launcher instalado |
| VS Code automatizado | Cliente/restart/confiança, estrutura do VSIX, conclusões e 611 entradas de API/paletas aprovados |
| VS Code gramáticas reais, sem teste visual | 55 casos TextMate/embutidos e 40 verificações de concatenações, mais isolamento/cancelamento/3.000 fragmentos, aprovados |
| Sublime automatizado | Pacote, conclusões e 43 casos de recorte, incluindo 3.000 fragmentos, aprovados |

Os testes condicionais que exigem MariaDB configurado, autenticação com DNS real
ou chave DNSSEC específica não foram exercitados, nem contados como aprovados.
O Electron em modo Node emitiu um aviso de codesign do ambiente, mas o teste de
gramáticas terminou com código zero. Não é evidência de teste visual no editor.

Durante a bateria geral apareceu uma falha intermitente no fixture HTTP do
Carteiro: a asserção recebia somente o primeiro trecho TCP do HTML. O teste foi
corrigido para acumular o corpo conforme `Content-Length`, com limite de 4 MiB,
timeout existente e leituras de 4 KiB para exercitar fragmentação. Nenhum código
da aplicação Carteiro foi alterado. O leitor inicial do teste corrigido usava
uma classe de padrão Lua não aceita em Santafé; foi substituída por `[ \t]*`.

Hashes dos artefatos efetivamente exercitados:

```text
8c7e817b87d36ea5bfab6701a844e89c85edb178c83a47359665c88a2c6c06b3  src/santafé
fe44c750fd9d972858bb9e841bf17cfc000a45572fad3f41ae532b2d171390fb  ferramentas/sls/sls.fé
```

Relatório local do alvo: `/tmp/sls-etapa1-20261021.json` (temporário).
Log local da regressão: `/tmp/santafe-sls-etapa1-regressao-final.log` (temporário).
O relatório JSON identifica a árvore modificada; o commit-base não representa
sozinho estes bytes não registrados.

## Limites e próximo marco

O espelho do documento é incremental, **não a árvore sintática**: linhas e
sintaxe são reanalisadas integralmente. A API retorna o primeiro erro; não há
AST reutilizável, recuperação de múltiplos erros, escopos, símbolos vinculados,
validação interna das expressões de gabaritos nem cancelamento em andamento.
Esses itens permanecem explicitamente no contrato de evolução.

Não foram instaladas atualizações no Mac, servidor remoto ou editores reais;
não houve publicação, push, etiqueta, teste Linux/Windows ou teste WebAssembly
novo. A API nova não existe nos binários públicos 2.0.3: núcleo e SLS deverão
ser distribuídos juntos em uma versão futura, sem sobrescrever aquela versão.
Os pacotes dos editores gerados pelos testes são artefatos locais de trabalho,
não novos lançamentos 1.0.7/1.0.13 para publicar.

A primeira entrega solicitada está implementada e ensaiada localmente. Isso
não encerra a homologação da 0.2 nem libera a 1.0. O próximo marco é a base
estrutural com escopos/símbolos e recuperação sintática, conforme
[SLS 1.0](SLS-1.0.md); o repositório de bibliotecas continua separado.

## Reprodução

```bash
make cbin
src/santafé testes/bibf/teste_analise_sintatica.fé
python3 testes/integracao/testar_analise_c.py
python3 testes/integracao/testar_sls_incremental.py
python3 testes/integracao/testar_sls_infraestrutura.py
python3 testes/integracao/testar_sls_aceitacao.py --perfil atual
python3 testes/integracao/testar_sls_aceitacao.py --perfil 1.0 \
  --relatorio /tmp/sls-etapa1-20261021.json
# A saída 2 acima registra capacidades ainda pendentes. Separadamente:
GSETTINGS_BACKEND=memory bash testar.sh
```
