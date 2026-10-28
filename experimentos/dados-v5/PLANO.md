# dados.5 — aplicativos e ciclo de instalação isolado

Autorização: homologar aplicativos completos, instalação, atualização e
rollback; corrigir pendências e preparar candidato, sem produção.

Escopo de aplicativos desta árvore: Correio (recebedor, agência, IMAP, envios),
Carteiro e Nomes (autoridade e resolvedor). Pão do Café é projeto independente;
não acessar seus arquivos operacionais ou banco. Usar dados fictícios e
MariaDB própria, portas altas de loopback, depósitos/PULSO temporários.

1. Partir do arquivo dados.4 com hash conferido; preservar árvore/artefatos.
2. Corrigir fechamento da instalação SLS: estrutura.fé e ONFÉ não acompanhavam
   a cópia oficial; ONFÉ ainda apontava para experimentos fora do prefixo.
3. Executar processos de aplicação, não apenas módulos, e validar percursos
   SMTP/IMAP/HTTP/DNS. Não enviar mensagens nem consultas ao mundo externo.
4. Exercitar prefixo novo, atualização e falhas/rollback com preservação de
   arquivos de terceiros. Não executar sudo, systemctl, scripts históricos
   de publicação ou migrations em banco empresarial.
5. Repetir no Debian, regressões e integridade; registrar gates ainda abertos.

## Estado após os ensaios

- Instalação SLS corrigida e comprovada fora do fonte.
- Encontrado envio interrompido por lista JSON recusada no retransmissor;
  migração explícita, destinatários visíveis/ações do Carteiro e regressão
  adversarial registrados em `aplicar.py` e `testar-fronteiras.fé`.
- Treze percursos completos passaram nos dois sistemas. Banco e serviços de
  laboratório encerrados; mensagens fictícias preservadas só nos logs/depósito
  temporários. Nenhum banco operacional foi consultado.
- Instalação, oito pontos de falha/rollback, reinstalação, remoção seletiva e
  transição dados.4 → dados.5 → dados.4 conferidos. Guardas bloqueiam o fluxo
  público ainda estável no pacote candidato.
- Regressões da cadeia, bibliotecas, SQL, SLS, núcleo/ONFÉ e WASM repetidas;
  limites operacionais e de cobertura enumerados no relatório.
- Próxima ação: fechar a entrega verificável, conservar dados.4 e entregar
  dados.5 para avaliação. Não promover candidato experimental a versão estável.
