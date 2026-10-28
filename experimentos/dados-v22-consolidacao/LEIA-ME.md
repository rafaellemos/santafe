# Consolidação da próxima versão maior

Esta preparação integra a base de fontes Windows dados.21 com a bateria de
macOS, Debian e WebAssembly. Núcleo, SLS, ajuda, editores candidatos e ensaios
de instalação devem identificar dados.22. Nenhuma regra de comportamento é
relaxada. Os arquivos históricos continuam identificando suas rodadas.

O preparador exige a base selada pelo SHA-256 e um diretório novo. A compilação
e os testes só ocorrem nessa cópia; o instalador público continua bloqueado.
Não reutilizar `operação/publicar-conjunto.sh` da versão 2.1: ele tenta importar
bibliotecas antigas e não migra toda a instalação para IBA3.

A validação auditiva foi deixada para uma etapa futura pelo usuário. Ela não
está aprovada. O instalador Windows permanece sem assinatura pública; a
publicação direta precisa informar essa condição e não orientar a desativar
proteções. Uma resposta ou aprovação da SignPath não é presumida.

Próximos critérios para publicação: regressão desta fonte integrada;
identificação final da versão; instalador e distribuição coerentes; migração
operacional com reversão ensaiada sobre a mesma fonte; conferência final do
usuário. A bateria Windows anterior continua sendo evidência de dados.21,
não de um MSI futuro com outra identidade.

Execute o preparador com a base `santafe-dados21-fontes-windows.tar.gz` e um
destino novo. No destino, use `testar.py --etapa compilar`, depois `regressao`,
`bibliotecas` e, no Debian com Emscripten, `wasm`. `regressao` exige os caminhos
reais `SANTAFE_ESTAVEL` (2.1) e `SANTAFE_DADOS7` (migração dos delimitadores).
`aplicativos` usa banco descartável e portas locais, nunca os ambientes ativos.

A reserva mínima é 2 GiB; os bancos descartáveis exigem ainda 128 MiB livres
antes de iniciar e usam log InnoDB de 16 MiB para limitar seu consumo. As
asserções, quantidade de operações e duração da carga não foram reduzidas.
A etapa `banco` executa os doze percursos SQL/postais que a matriz sem banco
registra como ignorados (mais o contrato SQL nulo). Resultados e falhas ficam em `evidencias/`; somente
resultado PASSOU confirma a etapa executada. Testes antigos não executados
novamente devem ser referenciados com sua origem e limites.
