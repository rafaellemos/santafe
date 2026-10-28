# Santafé dados.12 — homologação

Não instalar em produção. Esta entrega mantém a IBA `santafe-3` e não promove
a versão estável. Consulte ESTADO.json e RELATORIO.md.

- `preparar.py`: deriva os fontes selados dados.11.
- `aplicar.py`: separa os temporários MariaDB de cada instância de teste.
- `testar-temporarios.py`: prova de limpeza/preservação de sentinela, em área privada.
- `carga-replica.py`: reutiliza a réplica privada aprovada, com tráfego de leitura
  limitado e parada automática por orçamento de recursos. Novas escritas de
  teste e reversão são conferidas ao final.
- `exportar-evidencias.py`: exporta somente contagens de uma rodada concluída.

O roteiro depende de uma réplica de ensaio existente e de seus dados privados,
que não são distribuídos. Não executá-lo contra a instalação operacional.
Os diretórios temporários de MariaDB devem ser exclusivos também no bootstrap:
separar apenas banco, porta e soquete não protege os arquivos `#sql*`.

Os editores são kits experimentais 0.0.12. Não foram enviados a catálogos públicos.
Verifique a entrega com `sha256sum -c SHA256SUMS`; não há comando de publicação.

Para experimentar apenas o núcleo, extraia o arquivo de fontes em um diretório
novo dentro de `/tmp`, entre nele e compile sem instalar:

```sh
sh experimentos/dados-v3/construir.sh
./src/santafé -E -P -e 'local itens=[1,nulo,3]; mostre(tipo(itens), #itens)'
```

O resultado esperado do exemplo é `lista` e `3`. A construção requer as
ferramentas e bibliotecas de desenvolvimento usadas pelos ensaios; não altera
`/usr/local`, serviços ou bancos. Não execute `instalar.sh` para promover esta
revisão: o instalador público permanece bloqueado no candidato.

Para reproduzir a preparação e o empacotamento a partir do repositório de
trabalho, é necessária a entrega selada dados.11 indicada em `preparar.py`.
Os ensaios comparativos da IBA também utilizam os binários históricos 2.1.0 e
dados.7. A réplica completa depende da captura privada fornecida pelo operador;
esses dados não estão no pacote de fontes.
