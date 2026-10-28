# Santafé 3.0.0

Núcleo 3.0.0, IBA 3, SLS 1.1.0 e gerenciador de bibliotecas 1.1.0.
Extensões de editor 2.0.0 são distribuídas separadamente.

Esta versão maior exige migração dos projetos 2.1. Leia
`docs/CONTRATO-DADOS-ONFE.md` e `docs/manual.html` antes de atualizar.
Listas usam `[]`; tabelas continuam usando `{}`. Nulo passa a ser armazenável;
use `tabela.apague` para excluir uma chave. Colares brutos usam `[=[...]=]`
ou níveis maiores; `[[...]]` passa a ser interpretado como listas aninhadas.
Bibliotecas C devem ser recompiladas para a IBA 3.

Linux/macOS: `./instalar.sh` oferece as dependências e compila o conjunto.
Para instalação privada com dependências já disponíveis:
`./instalar.sh --sem-dependencias --prefixo /caminho/absoluto/santafe`.
Não execute este instalador genérico sobre um servidor operacional 2.1:
a atualização dos aplicativos e serviços exige o publicador de migração.

Windows x64: use o MSI por usuário ou extraia o pacote portátil do portal.
O pacote Windows contém núcleo, SLS, gerenciador e suas dependências;
não instala os serviços Linux de correio, DNS ou portal.
O MSI não tem assinatura Authenticode pública. Confira origem e SHA-256;
as proteções do Windows permanecem habilitadas.

No projeto: `santafé instale semver 1.0.0`. O catálogo e esse pacote imutável
continuam compatíveis com a 3.0. A instalação é local ao projeto.
SLS: `santafé-sls` no Linux/macOS, `santafe-sls.exe` no Windows.
Homologação auditiva e assinatura pública não fazem parte desta entrega.
