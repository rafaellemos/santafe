# Distribuição 3.0.0-rc.1 — dados.23

Candidato de homologação. Não publicado, não instalar em produção.

O contrato de listas, nulo armazenável, ONFÉ e IBA3 agora é o padrão do núcleo
e do SDK. Não é necessário passar uma opção experimental ao compilador.
Módulos C e C++ continuam obrigados a exportar `SANTAFE_MODULE_ABI`.
Os caminhos de bibliotecas e ferramentas passam a `santafé/3.0`; o descritor
IBA3 e o bytecode SF3 permanecem os mesmos do candidato anterior. O SLS e o
gerenciador desta distribuição identificam `1.1.0-rc.1`.

`preparar.py` exige o SHA256 da fonte dados.22 e confere seu manifesto antes
de criar um destino novo. `construir.sh` compila a distribuição sem habilitar
o contrato por opções de linha de comando. Os publicadores 2.1 e os comandos
globais de instalação continuam fora do caminho de homologação.

## Migração coordenada

`transacao.py` opera exclusivamente em uma réplica privada marcada. Prepara
cópias com SHA256, registra a intenção antes de cada troca, para os
consumidores na ordem inversa da inicialização e restaura o conjunto que
estava ativo. Arquivos de código/configuração são os únicos destinos
admitidos. Bancos, depósitos postais e certificados servidos não são destinos.
O diário permite recuperar uma interrupção entre gravação e substituição.
Deriva de arquivos, ligações simbólicas, ligações físicas e cópias corrompidas
impedem a troca ou a reversão. Um conflito durante a reversão exige revisão;
não é resolvido sobrescrevendo alterações posteriores.

A raiz é privada e pressupõe ausência de outro escritor com o mesmo usuário
fora do protocolo de trava. Não é uma fronteira contra administrador hostil
ou outro processo com privilégios equivalentes. `fsync` foi exercitado; uma
perda elétrica física não foi simulada.

`testar-transacao.py` cobre as falhas com supervisão controlada e términos
abruptos reais. `testar-distribuicao.py` instala os artefatos compilados em
prefixo privado e troca dois processos reais do núcleo entre 2.1 e 3, incluindo
módulos nativos, ajuda e falha de saúde. Esses testes não equivalem à réplica
completa com MariaDB, SMTP/IMAP e supervisão systemd. O adaptador operacional
e a revisão semântica dos arquivos capturados ainda são etapas obrigatórias.

## Reproduzir

Depois de preparar a fonte em diretório novo:

```sh
python3 experimentos/dados-v23-distribuicao/testar.py compilar
python3 experimentos/dados-v23-distribuicao/testar.py regressao
python3 experimentos/dados-v23-distribuicao/testar.py bibliotecas
python3 experimentos/dados-v23-distribuicao/testar.py transacao
```

`regressao` precisa de `SANTAFE_ESTAVEL` (binário real 2.1.0) e
`SANTAFE_DADOS7` (referência dos delimitadores). `transacao` precisa de
`SANTAFE_ESTAVEL`. A etapa `wasm` exige Emscripten/Node já disponíveis.
O roteiro preserva uma reserva mínima de 2GiB; não apaga ensaios antigos.

Novos MSI e pacotes oficiais dos editores ainda precisam ser reconstruídos e
validados com estas identidades/caminhos. Aprovações Windows dados.21 e a
inspeção dos editores anteriores não são aprovação automática de artefatos
novos. A assinatura pública continua pendente; a validação auditiva foi
adiada pelo usuário, sem declaração de aprovação.
