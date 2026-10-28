# Dados.15 — preparação da homologação ACME pública

## Conclusão e isolamento

Há uma forma de homologar a emissão pública sem substituir certificados ou
interromper o serviço: reutilizar a rota HTTP-01 existente do Pão do Café,
com desafios temporários e Certbot totalmente separado em /var/tmp. O caminho
foi conferido em leitura no servidor. A rota do Santafé usa o plugin nginx;
essa alternativa foi evitada porque poderia editar sua configuração.
O DNS secundário não estava acessível por SSH nesta inspeção; não se alterou
sua rede para transformá-lo em laboratório público.

O acesso SSH atual não tem sudo sem senha. O roteiro foi preparado, ensaiado
e enviado para execução pelo usuário. Não houve pedido a uma CA pública
nesta preparação. Não confundir os três grupos de ACME local com aprovação
de emissão pública. O certificado vigente continua servido pela produção.

## O que o roteiro verifica

A conta deve corresponder à CA Let's Encrypt de produção e estar válida.
Configuração global do Certbot não é herdada: um arquivo vazio explícito e
diretórios privados impedem mistura com renovações e hooks operacionais.
Não há --agree-tos, instalação, plugin nginx, standalone, reinício ou alteração
de timers. O domínio e os caminhos de produção são fixos e não aceitam
substituição por argumentos. As ordens públicas ficam limitadas a emissão e
renovação; as tentativas não são repetidas automaticamente.

A autorização cria arquivo exclusivo, rejeita travessia e links, verifica a
resposta HTTP e guarda a identidade e o hash do arquivo. A limpeza recusa
apagar conteúdo modificado por outro processo. Diretórios temporariamente
criados no webroot só são removidos se vazios. Conta e certificados de teste
permanecem privados, fora do fonte e da distribuição.

Certificado: SAN exato, prazo, cadeia confiável, chave correspondente e mudança
após renovação. Antes/depois: hashes dos arquivos nginx/Let's Encrypt/núcleo,
identidade e tempo inicial de oito processos (incluindo nginx), certificados
servidos e quatro rotas HTTPS. Uma renovação operacional concorrente também
produzirá diferença e impedirá aprovação: o roteiro não tenta revertê-la.

## Evidência nova

Doze grupos adversariais do auxiliar passaram em macOS e Debian: autorização
e limpeza, travessia/domínio/valor inválidos, colisões, links simbólicos,
alteração por terceiro, falha HTTP, subprocesso/tempo limite, comandos isolados
e conta existente. Houve duas falhas de preparação no macOS: o sandbox
inicial não permitia bind em loopback e /tmp é link para /private/tmp. Foram
usados o acesso local autorizado e o caminho canônico do laboratório, sem
relaxar a recusa de links nos caminhos operacionais.

No Debian, Certbot 2.1 e Pebble reais passaram três grupos com o novo auxiliar:
emissão com desafio HTTP e limpeza; renovação com novo desafio e certificado;
CA indisponível preservando o certificado vigente. O namespace tinha somente
loopback; domínio da aplicação no DNS exclusivo do laboratório, nenhuma saída para a Internet.
Certificados locais foram verificados contra raiz privada apenas do teste.

As regressões do candidato foram repetidas em macOS e Debian: dez etapas
principais/11 subetapas, IBA/SDK 14 grupos, instalação cinco, reversão sete e
gerenciador. WebAssembly: 18 casos e recuperação após erro. Os kits mantêm as
gramáticas da dados.14, alterando apenas metadados de versão e READMEs. A primeira
bateria macOS parou por Node ausente no PATH; a repetição usou o runtime instalado,
sem dispensar os testes de cores. Não houve nova inspeção visual do candidato:
as janelas inspecionadas ainda pertenciam ao ambiente dados.8.

## Evidência herdada e limites

A base selada é dados.14, SHA-256 dos fontes
`ddca28b7e058795ab5ff5d15a412ee8517962d421279df3bee20812cca47e5ce`.
Núcleo/bibliotecas/contrato de dados não receberam nova funcionalidade. A carga
integrada de uma hora (43.176 pedidos), 21 grupos e seis grupos de imagens após
reversão pertencem à dados.14 e não foram repetidos nem atribuídos à dados.15.
Mailjet: um envio da dados.13 recebido com acentos corretos, confirmado pelo
usuário; nenhum envio adicional nesta revisão.

Continuam sem homologação Windows/ARM, perda elétrica real e nova inspeção
visual desta revisão. A base estável capturada continua com HTTP 500 em
/entrar sem destino; o candidato responde 200. A reversão preserva o estado
capturado e não é uma correção retroativa da base. Não há promoção estável,
publicação de catálogos, push ou etiqueta automáticos.

Referências primárias consultadas:
[Certbot: certonly, diretórios e hooks](https://eff-certbot.readthedocs.io/en/stable/using.html),
[Let's Encrypt: HTTP-01](https://letsencrypt.org/docs/challenge-types/),
[ambiente de homologação e contas separadas](https://letsencrypt.org/docs/staging-environment/).
