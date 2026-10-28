# Santafé dados.13 — homologação das integrações

Não instalar em produção. Consulte ESTADO.json e RELATORIO.md. A entrega não
promove a versão estável e não altera serviços, catálogos públicos ou o Git.

Verifique `sha256sum -c SHA256SUMS`. Para experimentar o núcleo, extraia os
fontes em um diretório novo em `/tmp`, entre nele e execute:

```sh
sh experimentos/dados-v3/construir.sh
./src/santafé -E -P -e 'local itens=[1,nulo,3]; mostre(tipo(itens), #itens)'
```

Resultado esperado: `lista` e `3`. Não execute o instalador público, que continua
bloqueado para candidatos. Os kits experimentais dos editores são 0.0.13.

## Roteiros

- `testar-servicos.py --portal CAMINHO_DA_COPIA`: ClamAV, SMTP, triagem nativa e
  upload do portal com banco e arquivos sintéticos, em namespaces sem rede externa.
- `testar-acme.py --dependencias DIRETORIO_PRIVADO`: Certbot/Pebble, emissão,
  renovação e falha. Usa CA e confiança privadas, sem certificados públicos.
- `testar-rede-publica.py --credencial-capturada CAMINHO_PRIVADO`: DNS, TLS e
  autenticação Mailjet somente. Não envia mensagens. Credencial fica no servidor.
- `testar-dkim-publico.py INDICE_PRIVADO`: verifica assinaturas com DNS público e
  recusa adulterações em memória; não modifica nem exporta mensagens.
- `migrar-portal.py COPIA_DO_PORTAL`: corrige o upload na cópia privada; compila
  antes da troca e guarda o original. `--reverter` restaura apenas se os hashes
  continuam correspondendo, sem descartar edições posteriores.
- `testar-migracao-portal.py COPIA_DO_PORTAL`: testa os quatro casos de aplicação
  e reversão em outra cópia temporária; não escreve na réplica fornecida.
- `exportar.py`: esquema fechado de rótulos, contagens e hashes; exclui conteúdo
  de mensagens, ambientes, contas e registros privados.

O portal empresarial Pão do Café não integra o produto Santafé. Os fontes e
dados das réplicas não são distribuídos. A correção do portal Santafé está
incluída como transformação operacional conferida, para aplicação à cópia
migrada. Não foi aplicada à produção nem à réplica original da carga dados.12.

Para reconstruir esta preparação, é necessário o arquivo de fontes selado
dados.12 indicado em `preparar.py`. `empacotar.py` registra as diferenças e
produz um arquivo determinístico. Os ensaios da IBA usam os executáveis
históricos 2.1.0 e dados.7; os ensaios externos requerem as dependências
descritas no relatório, sem instalá-las automaticamente no sistema.

Continuam pendentes o envio real e a confirmação de recebimento pelo Mailjet,
além da emissão/renovação pública. Não interrompa as filas existentes para
esses testes. Uma caixa de teste precisa ser indicada antes de qualquer envio.
