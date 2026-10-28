# Homologação operacional dados.24

Esta entrega usa o núcleo 3.0.0-rc.1 e o SLS/gerenciador 1.1.0-rc.1 da fonte
dados.23, sem alterar os seus fontes C. É uma nova rodada de migração
operacional, não uma versão publicada nem autorização para instalar.

`preparar.py` exige o arquivo fonte23 selado e um destino novo. Ele confere
SHA256 e os 897 conteúdos antes de criar o laboratório. Os arquivos históricos
ficam intactos; `replica-base.py` é uma cópia adaptada do ensaio anterior.

`migrar.py` só funciona no Linux, com a captura privada autorizada e uma
restauração previamente conferida. Ele cria namespaces próprios de rede,
processos e montagens. Não há interface externa, rota padrão, conexão ao
Mailjet ou administração do systemd operacional. Os bancos e os depósitos
utilizados são cópias; nenhuma configuração capturada chega à produção.

A transação troca arquivos de código/configuração na mesma raiz privada,
coordena oito consumidores reais e conserva uma fila de teste inativa.
O nginx do laboratório permanece como infraestrutura; sua configuração TLS
de teste não é parte da atualização do núcleo. As configurações de DNS
`.fé`/`.env` são admitidas; chaves, certificados, bancos e depósitos não são
destinos. O supervisor lê a identidade do binário antes de cada início.

Além da atualização e reversão explícita, o ensaio provoca uma falha de
saúde depois de receber mensagens nos dois domínios. A reversão deve manter
essas mensagens, todos os objetos e o conjunto de consumidores ativos.
Não se restaura o banco para desfazer uma troca de código.

As adaptações de Pão do Café pertencem à cópia operacional do projeto
empresarial; não o incorporam ao fonte genérico da plataforma.

Dados capturados, arquivos de ambiente, fontes operacionais privados e
registros detalhados permanecem no servidor. Somente contagens, resultados
e hashes podem acompanhar o relatório público.

Não há comando para publicar em produção nesta entrega. Windows, pacotes
oficiais dos editores, assinatura pública e uma captura operacional atualizada
precisam ser tratados antes da publicação estável. A validação auditiva foi
adiada pelo usuário, sem alegação de aprovação de acessibilidade.
