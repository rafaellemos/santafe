# Escalabilidade e implantações externas

## Fronteira

Santafé fornece linguagem, bibliotecas e serviços reutilizáveis. Uma empresa
que usa Correio ou Carteiro é consumidora da plataforma, não componente dela.
O compartilhamento de servidor reduz custo, mas não transfere marca, site,
usuários, dados ou governança para o projeto Santafé.

O repositório da plataforma não deve conter nomes de clientes, domínios reais,
identidade visual, regras empresariais, credenciais, bancos ou publicadores
particulares. Testes multidomínio usam somente nomes reservados, como
`domínio.example`.

## Unidade de isolamento

Cada implantação externa possui, no mínimo:

- identificador estável e domínios aceitos;
- banco postal e credencial próprios;
- depósito de objetos próprio;
- fila e trabalhadores de saída independentes;
- chaves DKIM, certificados e políticas SPF/DMARC próprios;
- cotas e limites do Vigia próprios;
- cópias de segurança, retenção, registros e PULSO identificáveis;
- versão de configuração e ciclo de publicação independentes.

Um defeito, migração, bloqueio, restauração ou esgotamento de cota de uma
implantação não pode alterar dados nem interromper trabalhadores das demais.

## Compartilhamento permitido

Os seguintes elementos podem ser compartilhados enquanto houver capacidade:

- binários e bibliotecas instalados do Santafé;
- portões SMTP, submissão e IMAP;
- balanceadores e terminação TLS;
- servidores físicos ou virtuais;
- MariaDB e armazenamento como tecnologias, mas não as credenciais ou o
  espaço lógico de cada cliente;
- observabilidade agregada, desde que cada acontecimento conserve a origem.

Nenhum desses compartilhamentos é obrigatório. A mesma configuração precisa
permitir separar um cliente em outra máquina sem recompilar o núcleo.

## Configuração dos portões

`CORREIO_BANCOS_ADICIONAIS` relaciona domínio, prefixo de ambiente e depósito.
As credenciais correspondentes ficam fora do fonte, em
`/etc/santafe/correio-clientes.env`. Depósitos compartilhados pela unidade
systemd ocupam subdiretórios de `/var/lib/correio-clientes`.

Uma implantação que precise de outros caminhos instala um *drop-in* da unidade,
sem modificar o arquivo distribuído pela plataforma.

## Crescimento horizontal

Para aceitar mais de uma instância, componentes persistentes devem guardar o
estado durável no banco, fila ou depósito e usar operações atômicas. Em
particular:

1. Envios reserva cada carta com identidade, prazo e retomada segura.
2. Carteiro guarda sessões em repositório compartilhado ou usa bilhetes
   verificáveis; não depende da memória de uma instância.
3. Recebedor e Agência podem ser replicados atrás de distribuição TCP, desde
   que limites globais não existam apenas na memória local.
4. IMAP conserva UIDs, sinalizadores e bloqueios no banco; IDLE precisa de um
   canal de publicação entre instâncias.
5. Vigia aplica limites locais imediatamente e pode combinar contadores
   externos para políticas globais.

## Publicação

A plataforma publica contratos, migrações e binários. Cada projeto consumidor
fixa uma versão compatível e publica seus sites, unidades complementares,
segredos e configurações. Atualizar Santafé não deve reescrever o site de um
cliente; atualizar um cliente não deve substituir fontes do Santafé.
