# Preparação dados.21 — console Windows

Ainda não há pacote dados.21 nem aprovação Windows. O candidato dados.20 e seus
artefatos permanecem intactos. Esta pasta registra uma correção em preparação.

O ensaio visual do Windows10 Pro19045.2965 mostrou que `santafe -v`, iniciado em
um CMD novo com CP850, imprime os bytes UTF-8 como caracteres incorretos. A mesma
execução, com CP65001, apresenta corretamente Santafé, não e produção. O PATH e
o registro MSI3.0.20 estavam corretos. O banner interno ainda dizia dados.18.

O CLI proposto detecta os identificadores de console, prepara entrada e saída
UTF-8 e registra a restauração na saída normal. Não muda a configuração global
do Windows, o modo binário, arquivos, pipes ou o iniciador do SLS. Se não houver
console, não registra restauração nem altera páginas de códigos. Se a segunda
alteração falhar, desfaz a primeira. Uma alteração explícita para outra página
durante a execução é preservada. A identificação padrão passa a dados.21.

O uso de UTF-8 nas APIs de console exige a página65001 segundo a
[documentação Microsoft](https://learn.microsoft.com/en-us/windows/console/console-code-pages).
A restauração não é garantida se o processo for encerrado abruptamente. Esta
solução ainda precisa de ensaio real de entrada Unicode no console clássico.

Executado no Mac: 12 casos simulados das APIs, com ASan/UBSan e avisos tratados
como erro; verificação sintática do CLI na compilação não Windows. Isso testa
decisões, reversão e erros, **não** substitui a execução com as APIs reais.

Antes de gerar outro candidato:

- Compilar no ramo temporário Windows autorizado e repetir a bateria completa.
- Usar console real em CP850 e CP65001; conferir versão, erros e entrada NFC/NFD.
- Conferir emoji e fonte do console, distinguindo ausência de glifo de erro de codificação.
- Conferir restauração após sucesso, erro, encerramento pela biblioteca e interrupção.
- Comparar bytes de stdout/stderr redirecionados, inclusive binários; repetir SLS39.
- Ensaiar stdin redirecionado com stdout console e a combinação inversa.
- Repetir os casos no Windows10 e11; então integrar receitas, manifestos e instalador.

As capturas e a observação original estão em
`homologacao/windows-dados20/FIRMAMENTO-WINDOWS10-CONSOLE-OBSERVADO.json`.
Nenhuma alteração foi instalada, enviada ao GitHub ou aplicada à produção.
