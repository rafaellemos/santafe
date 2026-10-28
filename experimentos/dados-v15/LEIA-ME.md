# Santafé dados.15 — homologação pública ACME preparada

Não instalar em produção. Candidato de homologação; promoção estável pendente.
SLS 1.0.0-dados.15, IBA santafe-3, extensões experimentais 0.0.15.

A emissão pública usa a rota HTTP-01 já configurada no Pão do Café. Não é
necessário criar subdomínio, trocar DNS ou parar o site. A única escrita
transitória no webroot é o desafio ACME, removido ao final. Configurações,
certificados servidos e processos da produção devem permanecer iguais.
A conta ACME existente é copiada somente para diretório privado no servidor;
nenhuma conta é criada e nenhum termo é aceito automaticamente.

O roteiro faz até duas ordens na CA pública: emissão e renovação. Usa
`certonly`/`renew` com configuração, conta, logs e certificados separados em
`/var/tmp/santafe-acme-publico15-*`, sem plugin nginx, instalação, hooks de
serviços ou alteração de timers. Diretórios são privados de root. A cópia de
chave da conta e as chaves novas não devem ser exportadas.

O roteiro já está no servidor, com o mesmo hash da entrega:

```sh
sudo python3 /tmp/homologar-acme-publico-dados15.py --executar
```

Isso executa uma homologação, não publica o candidato. Exige sudo somente
porque a rota de desafios pertence ao servidor web. Ao terminar, informe
`RESULTADO_ACME` e `EVIDENCIA_PRIVADA`. Não envie chaves ou logs completos.
Só `PASSOU_EMISSAO_RENOVACAO_PUBLICA` confirma emissão/renovação, desafio HTTP
observado, limpeza e preservação da produção. Se a CA reutilizar autorização
anterior, o resultado registra essa limitação, sem fingir um novo desafio.
Se ocorrer falha, não repita automaticamente: examine a evidência primeiro.

Conferência da entrega, sem executar o candidato:

```sh
sha256sum -c SHA256SUMS
```

O ensaio real ainda depende da execução privilegiada pelo usuário. Os testes
Certbot/Pebble desta entrega são locais e não substituem esse resultado.
Consulte RELATORIO.md e ESTADO.json para os limites restantes.
