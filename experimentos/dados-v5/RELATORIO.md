# dados.5 — homologação isolada, 23/10/2026

O candidato avança a partir do dados.4; continua experimental. Foram usados
processos reais dos aplicativos desta árvore, não só repositórios simulados.
Produção, bancos empresariais, portal, catálogo, editores instalados e Git remoto
permaneceram sem alteração.

## Correções comprovadas

- Instalação SLS: `estrutura.fé` e ONFÉ agora acompanham o prefixo; o servidor
  não tenta mais buscar ONFÉ em `experimentos` fora da instalação. A remoção
  conhece esses arquivos e preserva arquivos alheios.
- O retransmissor recusava os destinatários recuperados da fila JSON porque
  ainda exigia `tabela`. Aceita agora lista explícita ou tabela densa revisada,
  preserva a parte local Unicode, normaliza o domínio e recusa entradas vazias,
  esparsas, mistas ou nulas, sem perder destinatários silenciosamente.
- O Carteiro reconhece listas nos destinatários visíveis, participantes,
  impressão e operações por IDs. Intervalos da política de entrega também
  admitem listas. Essas adaptações estão somente no candidato e possuem
  registro explícito em `MIGRACAO-APLICATIVOS.json`.
- O fluxo público de instalação foi bloqueado no pacote experimental para
  não recompilar inadvertidamente pelo contrato estável. Os testes usam os
  artefatos experimentais e as etapas reais de cópia em diretórios privados.

## Baterias executadas

| Bateria | macOS Intel | Debian 12 x86-64 |
| --- | --- | --- |
| Aplicativos: 13 percursos de integração | passou | passou |
| Instalação em caminho com espaços, módulos, CLI, SLS e ONFÉ | passou | passou |
| Reinstalação idempotente e preservação de arquivos do usuário | passou | passou |
| Rollback: seis etapas, cópia ausente e falha de saúde | passou | passou |
| Atualização real de componentes dados.4 → dados.5 → dados.4 | passou | passou |
| Remoção dos arquivos conhecidos, sem apagar arquivos alheios | passou | passou |
| Dez grupos da cadeia: pacotes, CLI, HTTPS, catálogo, limites, Unicode e datas | passou | passou |
| Bibliotecas: 76 aprovadas; 11 separadas para banco real | passou | passou |
| MariaDB temporário: 12 ensaios (os 11 acima mais NULL) | passou | passou |
| SLS: 39 adversariais/incrementais + 39 de aceitação LSP | passou | passou |
| Núcleo: 38 verificações; ONFÉ: 34; fronteiras PULSO/JSON | passou | passou |
| Compilação sintática de aplicativos/bibliotecas Fé | passou | passou |
| WebAssembly: 16 casos + recuperação após erro | — | passou |

Não somar essas linhas como testes unitários homogêneos. Alguns são grupos
com múltiplos cenários. A matriz de bibliotecas foi repetida depois da correção
do retransmissor/Carteiro. A regressão adicional `testar-fronteiras.fé` confere
listas/tabelas densas, rejeições e destinatário visível na impressão.

### Percursos dos aplicativos

1. Recebedor, Agência, IMAP e Carteiro iniciam com MariaDB exclusiva; HTTP
   exige sessão válida e redireciona anônimos com 303.
2. SMTPUTF8 recebe MIME e anexo reais no depósito; rejeita relay não autorizado.
3. Carteiro lista/lê o recebido, devolve o original byte a byte e o PDF, e
   recusa POST com CSRF inválido.
4. Agência exige autenticação, aceita SASL PLAIN Unicode sob STARTTLS, recusa
   senha errada e falsificação do autor visível e enfileira a mensagem válida.
5. TLS implícito também autentica; os clientes conferem o certificado de teste.
6. O executável Envios consome a fila e entrega ao recebedor local; o banco
   confirma o estado entregue e a nova mensagem recebida.
7. IMAP exercita AUTH, SELECT, UID SEARCH/FETCH/COPY, COPYUID, STORE, EXPUNGE
   e APPEND, inclusive a recusa de autor alheio no rascunho.
8. HTTP move para Lixeira, restaura em lote para Arquivadas/Todas e esvazia;
   a persistência é conferida diretamente no banco próprio.
9. O compositor HTTP enfileira; Envios entrega; Entrada e Enviadas persistem.
10. Reinício de IMAP/Carteiro preserva IDs, UIDs, pastas e tamanhos.
11. Nomes autoridade responde A/NXDOMAIN por UDP/TCP.
12. Nomes resolvedor usa raiz injetada de loopback, responde/reutiliza cache
    por UDP/TCP e aplica ACL. O contrato existente descarta UDP e fecha TCP
    para origem proibida; não promete resposta REFUSED.
13. PULSO dos processos permanece JSON válido/interoperável.

As primeiras execuções ajustaram expectativas do harness: 303 em vez de 302;
SASL Unicode explícito no Python; nomes publicados `Lixeira`/`Rascunhos`;
autor do rascunho correspondente à caixa; ACL silenciosa. A recusa de listas
do retransmissor foi falha real de implementação, não expectativa relaxada.
A falha de saúde injetada no SLS pode produzir EOF ou BrokenPipe; ambos levam
ao rollback e à nova verificação completa dos hashes/saúde do prefixo.

### Instalação e restauração

As etapas reais `bin`, `sls`, `pacotes`, `c`, `fe`, `pc` copiaram os artefatos
compilados. O prefixo com espaços executou núcleo, cinco módulos C, bibliotecas
Fé, CLI e SLS com documentos Fé/ONFÉ. Após interrupções injetadas, cópia ausente
e ONFÉ quebrado, os snapshots restauraram arquivos/permissões e passaram de novo
pelos testes de saúde. A atualização entre candidatos confirmou os componentes
4, depois 5, depois 4, mantendo o arquivo ONFÉ persistido e hashes anteriores.
Para instalar a geração 4 foi necessário somente o fechamento/relocação SLS;
a árvore anterior não foi modificada. Rollback não significa reverter decisões
de usuários nem apagar dados criados depois de uma atualização operacional.

## Evidências e limites

Árvore Mac: `/tmp/santafe-dados5-d6t53qnu`.
Árvore Debian: `/tmp/santafe-apps5.r8kBLsVH/arvore`.
Resultados preservados em `dist/candidato-dados-v5/evidencias/{macos,debian}`.
Pacote, manifesto e WASM em `dist/candidato-dados-v5`.

Isto fecha os percursos automatizados enumerados, não uma homologação universal:

- Não houve publicação, troca por systemd/nginx, entrega pela Internet/Mailjet,
  consulta pública DNSSEC, antivírus externo ou carga prolongada. TLS é de teste;
  a retransmissão é local sem TLS, e a verificação postal externa fica desligada.
  Os contratos de módulos de TLS/DKIM/DNSSEC/antivírus passaram nas baterias,
  mas não substituem testes operacionais com provedores reais.
- Atualização/rollback da distribuição pública estável para a futura versão
  maior ainda precisa de publicador e migração próprios. A simulação usa
  snapshots de um prefixo exclusivo, sem concorrência nem corte de energia.
- Sem nova inspeção visual dos editores/navegador, Windows, macOS ARM,
  sanitizadores nesta rodada, ABI/bytecode definitivo ou manual público migrado.
  As mensagens do relatório LSP que recusam liberação automática são corretas.
- ONFÉ ainda requer fechar o gate de gravação atômica e a política de migração.
  Listas permanecem sem metatabelas; nenhuma alteração desse contrato aqui.

Próximo passo: revisar os gates restantes e preparar o publicador da versão
maior em laboratório. Este candidato não autoriza instalar a versão estável.
