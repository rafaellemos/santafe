# dados.9 — correção visual incorporada

24/10/2026. Candidato para homologação; não é a versão maior estável.

## Alteração

Derivado do arquivo selado dados.8, preservado por SHA-256. A correção do
VS Code aplica `fontStyle` em `light` e `dark`: no renderer 1.142.0, o estilo
na raiz da decoração ocultava as cores. A regressão cobre normal/oblíquo,
temas claro/escuro e 612 entradas do catálogo. Os kits isolados identificam-se
como 0.0.9; o SLS, como 1.0.0-dados.9. Não são versões dos catálogos públicos.

Não houve alteração da sintaxe de dados.8: listas `[]`, inclusive `[[1],[2]]`,
colares brutos `[=[...]=]` e níveis superiores, gabaritos com um acento grave,
comentários `--` e `--[[...]]`. Nulo armazenável e ONFÉ permanecem.

## Testes executados nesta rodada

macOS Intel e Debian 12 x86-64, com arquivos, portas e bancos de laboratório:

| Bateria | Resultado |
| --- | --- |
| Colares e migração | 14 grupos, inclusive comparação com estável e dados.7 |
| Fontes Fé | 183 compilações |
| Núcleo, ONFÉ, JSON/PULSO, arquivo legado, ABI | regressão de 11 etapas passou |
| Persistência atômica ONFÉ | 17 grupos em ambos |
| SLS | 39 testes, APIs ONFÉ, 200 edições e recuperação incremental de delimitadores |
| Manual | 174 exemplos compilados, 12 seguros executados; 264 contratos C e 351 Fé |
| Instalação privada | instalação, atualização, idempotência, falhas/rollback e desinstalação seletiva |
| Gerações operacionais | sete grupos: trocas, término abrupto, rollback, trava e integridade |
| Aplicativos completos | 13 percursos HTTP, SMTP, IMAP, Carteiro, DNS e PULSO |
| Carga de aplicativos | 60 segundos em cada sistema, dados sintéticos |
| Editores | 612 entradas API/cores; 25+45 casos TextMate/HTML/JS; 17+7 recorte Sublime; cinco Prism |
| WebAssembly | reconstruído no Debian; 18 casos e recuperação após erro |

Nas 300 leituras concorrentes durante 20 trocas de gerações, os leitores do
Debian observaram ambas as versões; os do macOS observaram somente a estável.
Não se atribui à execução macOS cobertura de alternância que ela não observou.
O baseline desse ensaio é uma cópia do núcleo 2.1.0, não uma réplica de produção.

## Hosts e inspeção visual

VS Code 1.142.0: oito grupos no Extension Host real, extensão 0.0.9 e SLS
1.0.0-dados.9. Sublime Text 4215: seis grupos com verificações explícitas e
sentinelas, pois o Python otimizado pode remover `assert`. Escopo exclusivo
`source.santafe-dados9-host-gslwbyhb` confirmado.

Capturas reais examinadas nos dois editores: paleta suave, atributo HTML e
comentário JS atravessando concatenações, níveis dos delimitadores, curingas
`®`/`Ⓡ` laranja normal, expressão interna como código, listas e comentários
sem vazamento visual observado. Capturas foram exibidas na conversa, não
arquivadas como PNG. Os JSONs de host e a inspeção de pixels são evidências
separadas. O nome do perfil temporário ainda contém dados.8; os hashes e a
versão ativa comprovam o kit dados.9. Fixtures restaurados, comando temporário
retirado e janela do VS Code recarregada. Perfis habituais preservados.

## Ocorrências preservadas e limites

A primeira regressão encontrou uma expectativa de versão dados.8 no teste de
instalação. Os identificadores foram corrigidos e a bateria inteira repetida.
Uma primeira execução dos aplicativos foi impedida pelo sandbox de loopback;
o ensaio autorizado fora dessa restrição passou. Um primeiro harness Sublime
reutilizou o namespace dados.8; foi corrigido para o namespace exclusivo dados.9
e repetido. As tentativas anteriores estão nos relatórios, não foram apagadas.

Nomes de alguns scripts/logs continuam dados7/dados8 porque são baterias
reutilizadas; seus resultados aqui foram produzidos pelo candidato dados.9.
Os testes de host usam fixtures sem executar o código exibido.

Nesta rodada não foram repetidos os sanitizadores/fuzzers extras de dados.8;
seus resultados históricos não contam como nova aprovação. WASM foi testado
sob Node/DOM mínimo, sem inspeção visual de navegador. Carga de 60 segundos
não equivale a soak prolongado. Não se ensaiaram Windows/macOS ARM, provedores
postais externos ou migração de bancos empresariais.

Para a versão maior estável ainda faltam: fechar ABI/bytecode e atualização
dos módulos, migrar/retornar uma réplica operacional completa, soak prolongado,
inspeção dos aplicativos e plataformas prometidas. A pendência visual dos
editores foi resolvida para as versões acima.

Entrega em `dist/candidato-dados-v9`, com fontes, manual, kits, WASM, evidências
e checksums. Servidor usado somente em `/tmp/santafe-dados9.TVessQnc`.
Produção, serviços, portal, catálogos, bancos empresariais, etiquetas e remotos
Git permaneceram sem alterações. Não há publicador de produção nesta entrega.
