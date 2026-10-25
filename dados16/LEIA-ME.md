# Candidato dados.16 — Windows nativo

Adaptação isolada do SLS e do gerenciador, baseada na fonte selada dados.15.
Estado: em homologação; consultar o relatório da última execução antes de usar.
Não é publicador e não altera a produção 2.1.0.

## Limites do alvo

- Ensaios no Windows Server 2022 x64, executáveis PE/UCRT64 sem MSYS/Cygwin.
- Diretórios locais NTFS; caminhos de rede, junções/reparse points, hardlinks
  e nomes de dispositivos/fluxos alternativos não são aceitos pelas ferramentas.
- Núcleo e ferramentas são candidatos. Bibliotecas C completas, serviços,
  instalador do Windows, persistência geral ONFÉ em NTFS e validação visual
  dos editores Windows têm homologações separadas ainda pendentes.
- Compilar bibliotecas C requer `--permitir-nativo` e compilador absoluto
  confiável em `SANTAFE_CC`. Compilação nativa não é uma caixa de areia contra
  código C malicioso. Não há execução automática de scripts de instalação.

## Garantias sob ensaio

Os arquivos são abertos componente a componente com `NtCreateFile`, relativo
a identificadores de diretórios já verificados. A enumeração também usa o
identificador. A substituição usa arquivo temporário privado, sincronização e
renomeação relativa no mesmo diretório. Isso prova visibilidade atômica sob
os testes; não se afirma resistência certificada a perda física de energia.

A trava usa `LockFileEx`; o diretório da trava permanece fixado até sua liberação.
Processos usam `CreateProcessW`, lista explícita de identificadores herdados e
Job Object atribuído na criação, com encerramento dos descendentes. O ambiente
é reconstruído sem segredos; executável e compilador não vêm do PATH do projeto.
O SLS usa canais binários e não executa fontes ou inicializadores do projeto.

Os testes incluem atualização interrompida em seis fases, recuperação, cache e
lockfile adulterados, TLS real em loopback, recusa de redução a HTTP, limites
de saída/prazo, junções e disputa de travas. A sonda de confinamento usa somente
arquivos sintéticos e ataca uma raiz deliberadamente modificável; não toca em
configuração do sistema nem em dados do usuário.

## Reprodução

A receita concreta está no ramo temporário `homologacao/windows-dados15` em
`rafaellemos/santafe`, workflow `homologacao-windows.yml`. `windows/preparar.py`
confere e extrai a base; `aplicar.py` confere todos os arquivos da sobreposição.
`testar.py` compila e testa. Os hashes e resultados ficam nos artefatos do job.
Não usar os arquivos anteriores com a mesma designação como prova desta revisão.

Referências de implementação: documentação Microsoft de NtCreateFile,
NtSetInformationFile/FILE_RENAME_INFORMATION, GetFileInformationByHandleEx,
LockFileEx e Job Objects.

Antes de subprocessos, a cadeia inteira é novamente fixada e comparada por
identidade. O diretório final mantém um arquivo de guarda privado e não removível
até o encerramento: NTFS recusa converter diretórios não vazios em reparse points.
Só negar compartilhamento de escrita NÃO protege contra FILE_WRITE_ATTRIBUTES;
a bateria inclui esse ataque e um controle positivo após liberar a guarda.
Referência: https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points
