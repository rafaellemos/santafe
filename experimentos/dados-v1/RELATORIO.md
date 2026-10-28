# Validação do candidato dados 1

Executado em 23 de outubro de 2026, macOS x86_64. Este é um candidato local de comportamento, não um lançamento nem homologação de produção.

## Resultados executados

| Verificação | Resultado |
| --- | --- |
| Compilação C isolada do candidato, com verificações de API | Passou, sem avisos do compilador |
| Teste C de lista, nulo, presença, exclusão e índices brutos | `API_C_DADOS_OK` |
| Comportamento do núcleo | `CANDIDATO_DADOS_OK`, 38 verificações |
| Parser/serializador ONFÉ, recusas e limites | `ONFE_CANDIDATO_OK`, 34 verificações |
| Analisador SLS com listas, recuperação e intervalos | `SLS_DADOS_SINTAXE_INTERVALOS_OK` |
| Bateria Python de integração | 10 testes passaram, incluindo subcasos de índices inválidos |
| JSON → ONFÉ → JSON | 500 estruturas geradas com semente fixa preservadas, incluindo nulos, vazios, acentos, inteiros de 64 bits e números fracionários |
| Migração de colares | Mesmo resultado no núcleo estável e no candidato; fonte original preservado |
| Bytecode | Candidato gera e lê sua assinatura separada; núcleo estável recusa o bytecode experimental |
| AddressSanitizer e UndefinedBehaviorSanitizer | Teste C e os 10 testes de integração passaram, sem diagnóstico desses sanitizadores |
| Núcleo recompilado sem a opção experimental | Mesma bateria cruzada passou; regressões JSON, metatabelas, gabaritos Unicode e analisador SLS estável passaram |
| Gramática TextMate experimental no runtime do VS Code | 9 casos passaram: listas, texto bruto, comentários, ®/Ⓡ, acentos e retomada depois do colar |
| Gramática Sublime | Estrutura YAML lida; não houve teste visual nem execução da gramática pelo Sublime |
| Scripts Python/shell e whitespace do diff | Validados |

O teste de mutação executa 3 mil operações de lista e compara com uma estrutura de referência, intercalando coletas de lixo. A bateria não constitui prova de ausência de defeitos nem medição de desempenho para produção.

## Correções encontradas durante a validação

- Nulo armazenado não podia ser confundido com término de um iterador nem usado como chave interna coletável.
- O cache de ausência de metamétodo precisava ser invalidado ao trocar uma associação nula por função.
- Escritas/leituras brutas da API C precisavam respeitar os limites de listas.
- O JSON precisava emitir inteiros sem conversão intermediária para `double`, usar 17 dígitos significativos como padrão para números fracionários do candidato e rejeitar nomes duplicados.
- O migrador precisava usar o valor léxico do colar antigo, preservando sua regra de primeira quebra de linha, e não apenas trocar delimitadores.

## Limites e próxima etapa

Não foram executados: testes de produção, Debian, Windows, WebAssembly, interfaces visuais dos editores, serviço LSP completo sobre o núcleo candidato ou migração de SQL/Correio/Carteiro. Não houve instalação, publicação, transferência ao servidor, alteração de banco, commit, push ou etiqueta.

Os pacotes dos editores são gramáticas experimentais independentes. O SLS completo ainda usa estruturas e caches com a semântica antiga; o teste realizado é do lexer, diagnóstico do compilador e analisador estrutural. HTML/JS embutidos e as integrações completas dos editores não são declarados concluídos.

A próxima etapa é homologar este contrato e então migrar bibliotecas e ferramentas, definir a ABI definitiva, concluir o transporte ONFÉ/JSON etiquetado e a escrita atômica, tratar os limites de gabaritos/Unicode e executar a matriz multiplataforma. O manual estável e os catálogos públicos continuam descrevendo a versão instalada.

## Evidências locais

Na execução original, os logs ficaram em `/tmp/santafe-dados-construcao.log`, `/tmp/santafe-dados-testes.log`, `/tmp/santafe-dados-sanitizado-build.log`, `/tmp/santafe-dados-sanitizado-test.log`, `/tmp/santafe-dados-baseline-build.log` e `/tmp/santafe-dados-baseline-test.log`. Os testes e os comandos de reconstrução ficam junto dos fontes e podem ser repetidos.
