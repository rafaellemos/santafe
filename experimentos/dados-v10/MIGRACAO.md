# Migração da instalação completa — gate ainda aberto

## Captura sem interromper produção

O coletor `capturar-replica.py` precisa ser executado com sudo pelo operador:

```sh
sudo python3 /tmp/capturar-replica-dados10.py --copiar-dados
```

Ele lê núcleo, cabeçalhos, módulos, aplicativos, portais, configurações, unidades
systemd, depósitos e os dois bancos independentes. Exporta os bancos em uma
única transação, sem travar tabelas; recusa tabelas não InnoDB. Não para serviços,
não instala executáveis, não muda contas, bancos, DNS ou catálogos. O resultado
fica em `/var/tmp/santafe-replica-dados10-*`, privado ao operador. Credenciais,
corpos de mensagens, SQL e chaves permanecem no próprio servidor. Não incluir
essa pasta nos artefatos públicos nem baixá-la para o Mac.

O SQL é transacional, mas a captura SQL+filesystem não é um snapshot atômico.
Por isso, são obrigatórios a conferência do manifesto e o cruzamento de TODOS
os hashes de objetos referidos pelas cartas, anexos e filas dos dois bancos.
Mudanças de esquema durante a captura também devem ser evitadas pelo operador.
Nenhuma ausência de arquivo pode ser ignorada para declarar a réplica completa.

## Verificação e restauração privadas

`verificar-replica.py CAMINHO` confere permissões, dono, arquivos regulares,
symlinks/traversal, SHA-256, árvores e unidades obrigatórias e presença dos dois
bancos. Não executa ambientes shell ou código da cópia.

`restaurar-replica.py CAMINHO` se relança num namespace Linux de usuário/rede,
confere que só há loopback e inicia um MariaDB exclusivo, sem TCP, eventos,
plugins externos ou importação local de arquivos. O dump é restaurado somente
nesse servidor. Todos os objetos postais referenciados são conferidos contra
SHA-256. Contagens e checksums de todas as tabelas ficam num baseline privado.
A base de teste é encerrada ao terminar, inclusive quando há erro.

Esse comando comprova restauração e integridade; **não declara homologação da
migração dos aplicativos**. Ele não executa unidades capturadas nem reativa
filas reais. Antes de iniciar aplicativos, destinos, credenciais, certificados,
portas, caminhos e envio externo precisam ser substituídos por recursos de
laboratório. A rede sem saída externa permanece obrigatória mesmo depois disso.

## Próximos gates, depois da captura

1. Inventariar executáveis, versões, configurações e arquivos de todos os
   serviços efetivamente instalados; incluir o Pão do Café como consumidor
   independente, mantendo banco/depósito separados.
2. Migrar colares pelo lexer estável. Revisar atribuições nulas, exclusões,
   construtores posicionais e fronteiras JSON; compilar não prova equivalência.
3. Recompilar módulos C para IBA3. Não reaproveitar o bytecode nem os módulos
   binários capturados. Comparar aplicativos estáveis/candidatos com o mesmo
   snapshot e testar portal, correio, duas interfaces, IMAP, filas e DNS.
4. Conferir IDs, UIDs, UIDVALIDITY, pastas, mensagens, anexos, estado de entrega,
   autores/envelopes e os dois bancos antes/depois. Gerar mensagens novas apenas
   entre endpoints locais controlados e conferir persistência após reinício.
5. Ensaiar atualização com falhas em cada fase e rollback sem perder as escritas
   posteriores à troca. Restaurar um dump antigo sobre mensagens novas não é um
   rollback aceitável. Não promover enquanto essa compatibilidade não existir.
6. Só então produzir o publicador operacional reversível, sujeito à homologação
   do usuário. O kit dados.10 não contém comando para alterar produção.

## O que foi testado separadamente

`testar-replica.py` cria somente dados sintéticos e ensaia corrupção, exposição,
symlink, traversal, banco ausente, recusa sem namespace, restauração dos dois
bancos e inconsistência SQL/depósito. Seu sucesso não prova que a instalação
real foi copiada ou migrada. O relatório deve conservar essa distinção.
