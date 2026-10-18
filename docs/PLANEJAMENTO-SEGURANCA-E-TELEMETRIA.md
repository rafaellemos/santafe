# Planejamento de segurança e telemetria

Este documento separa a base já implementada das etapas futuras. PULSO/1 já
fornece envelopes, enquadramento binário, destinos locais, proteção de dados
sigilosos e integração com Correio e Caminheiro. O Vigia 0.1.0 já protege as
conexões do Correio. O transporte remoto, o Forte, o atuador do FRR e a
mitigação automática continuam sendo planejamento.

## Proteção do Caminheiro e dos serviços autenticados

- Separar limites por endereço, sub-rede, identidade e volume global.
- Aplicar os limites antes de operações caras, especialmente Argon2id.
- Limitar conexões, requisições, corpos, cabeçalhos, tempo de inatividade e
  trabalhos simultâneos.
- Usar atrasos progressivos e bloqueios temporários sem permitir que um
  atacante bloqueie permanentemente a conta de outra pessoa.
- Emitir falhas genéricas, registrar eventos e fornecer métricas para um
  observador externo.
- Rejeitar cedo sob sobrecarga e manter memória, filas e trabalho de CPU com
  limites fixos.

## Vigia: proteção local dos serviços

O Vigia é um braço incorporado aos serviços persistentes. Trabalha de forma
independente na camada de aplicação, aplicando limites e bloqueios com o
contexto que cada serviço conhece. A primeira integração protege conexões e
comandos SMTP no Correio; requisições e rotas no Caminheiro, consultas em
Nomes e operações de usuário no Carteiro são as ampliações seguintes.

O Vigia não depende do Forte para a proteção básica. Mesmo sem transporte
remoto ou coordenador, conta ocorrências, controla frequência e concorrência,
rejeita excessos, aplica bloqueios temporários e publica pelo PULSO somente as
leituras e os sinais necessários.

O termo **sentinela** não pertence à API do Vigia. Ele fica reservado aos
operários internos do futuro Forte.

## Forte: controle de mitigação por telemetria

Objetivo: analisar dados de rede em tempo real e, quando houver evidência
suficiente de ataque, aplicar e retirar mitigações por meio do FRR e dos
provedores de trânsito.

### Componentes

1. **Vigias dos serviços**: protegem localmente a camada de aplicação e
   publicam acontecimentos sem depender do Forte.
2. **PULSO**: o Protocolo Unificado de Leituras, Sinais e Operações
   transporta observações, alarmes e confirmações por um canal autenticado,
   cifrado e resistente a repetição.
3. **Sentinelas do Forte**: operários especializados que acompanham os
   acontecimentos PULSO de um serviço ou domínio, interpretam seu contexto e
   compartilham as observações com o coordenador. Os sentinelas existem no
   Forte; não são processos obrigatórios por porta nem componentes do Vigia.
4. **Forte**: arcabouço em Santafé que agrega janelas de tempo, compara a
   linha de base, correlaciona sensores e cria uma proposta de mitigação.
5. **Sensor de rede**: componente nativo no Linux, preferencialmente baseado
   em eBPF/XDP, que resume fluxos e contadores sem entregar cada pacote à
   Santafé. Seus dados serão acompanhados por um sentinela especializado.
6. **Atuador**: processo mínimo e isolado, com permissões estritas, que aceita
   apenas ações previamente autorizadas e conversa com o FRR.
7. **Observador externo**: confirma ataques quando o enlace ou a placa do
   servidor estiver saturado. Deve usar uma rede de gerência separada ou
   executar fora da rede atacada.

O fluxo previsto é: serviço → Vigia → PULSO → sentinela → Forte. No
sentido inverso, uma operação autorizada percorre Forte → PULSO → serviço,
onde o Vigia a valida e aplica localmente. A indisponibilidade do Forte ou do
canal remoto nunca deve desativar os limites locais.

### Mensagens previstas

- `observação`: contadores agregados por destino, origem, protocolo e porta;
- `incidente`: anomalia detectada, evidências e grau de confiança;
- `proposta`: regra sugerida, alcance, motivo e duração;
- `mitigação`: ordem autorizada e identificador idempotente;
- `confirmação`: estado efetivamente instalado pelo atuador;
- `retirada`: remoção explícita ou automática da regra;
- `pulso`: estado do sensor, Forte, atuador e canal de gerência.

Toda mensagem de controle deve conter versão, origem, destino, sequência,
carimbo de hora, validade curta e autenticação criptográfica. Decisões não
devem trafegar somente por UDP nem depender da interface sob ataque.

### Níveis de mitigação

1. Limite local no serviço, antes da autenticação ou do trabalho caro.
2. Descarte local precoce com XDP/nftables, quando o enlace ainda suporta o
   volume.
3. Regra seletiva no provedor, por FlowSpec ou API acordada, para combinar
   origem, destino, protocolo e porta.
4. RTBH por destino como último recurso: preserva o restante da rede, mas
   torna indisponível o endereço atacado durante a mitigação.

O servidor não pode anunciar os prefixos de origem dos atacantes como se
fossem seus. Bloqueio seletivo de origens deve usar FlowSpec, filtros no
provedor ou uma plataforma de limpeza. RTBH normalmente anuncia o endereço
da vítima com uma comunidade acordada com o provedor.

### Travas obrigatórias

- lista fechada dos prefixos próprios que podem receber RTBH;
- menor prefixo possível e alcance máximo configurado;
- proibição de comandos livres ou configuração arbitrária do FRR;
- aprovação humana na primeira versão;
- confirmação por mais de um sensor antes da automação plena;
- validade curta com retirada automática, renovada apenas enquanto persistir
  a evidência;
- histerese para evitar alternância rápida entre anunciar e retirar;
- registro imutável de proposta, autorização, instalação e retirada;
- botão de interrupção e reversão manual fora do canal atacado;
- laboratório com FRR isolado antes de qualquer sessão de produção.

### Etapas

1. Telemetria passiva, painéis e alarmes, sem executar mitigações.
2. Propostas automáticas com aprovação humana e retirada temporizada.
3. RTBH automático somente para cenários bem caracterizados.
4. Integração seletiva com FlowSpec ou API do provedor.
5. Alta disponibilidade, sensores externos e exercícios periódicos.
