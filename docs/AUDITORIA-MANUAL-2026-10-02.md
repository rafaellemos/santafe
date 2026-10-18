# Auditoria do manual e da API pública

Data da auditoria: 2 de outubro de 2026.

## Escopo

Esta auditoria trata somente da plataforma Santafé e de suas bibliotecas.
Pão do Café é um projeto empresarial independente: pode compartilhar a
instalação do interpretador, do Correio e do Carteiro, mas não integra o
produto nem a documentação da Santafé.

## Resultado

- a estrutura do manual, suas âncoras e os exemplos executáveis continuam
  cobertos pelo validador;
- as bibliotecas padrão, MariaDB e Arquivo já estavam alinhadas ao fonte;
- foram documentadas as operações criptográficas de `segredo` usadas por
  DKIM e DNSSEC;
- foram documentados os contratos recentes de `rede` para TLS, DNS
  assíncrono, IDNA, pares da conexão e agendamento;
- a apresentação deixou de fixar o nome "Santafé 1.0", evitando que o texto
  introdutório fique obsoleto a cada linha da linguagem;
- a descrição de retransmissão postal passou a ser neutra quanto ao
  fornecedor. A escolha do retransmissor pertence à operação da instalação,
  não ao contrato da biblioteca.

## Proteção contra regressão

`site-sfdev/validar-manual.py` agora extrai as funções registradas em
`luaL_Reg` pelo núcleo e pelas bibliotecas C oficiais e exige uma entrada
correspondente no manual. Aliases condicionais de compatibilidade, que não
fazem parte do contrato corrente, ficam explicitamente excluídos.

A validação falha quando uma função pública nova chega ao fonte sem
documentação. Assim, a conferência deixa de depender somente de revisão
visual.

## Bibliotecas Fé

O manifesto `docs/API-PUBLICA-FE.tsv` agora declara a superfície estável das
bibliotecas escritas em Fé. O validador exige a presença de cada contrato no
manual e no arquivo-fonte correspondente. Símbolos não listados são internos
por padrão.

A rodada também fechou lacunas encontradas diretamente no fonte:

- `res:dados` no Caminheiro;
- `cd:entregueAvisoDaFila` no Correio;
- `nomes.acesso.pertence` em Nomes;
- as superfícies avançadas de `correio.multibanco` e
  `correio.transporte`.

Os módulos de formato `imagem_png`, `imagem_jpeg`, `imagem_svg` e o auxiliar
`rpdf_unicode` permanecem internos atrás das fachadas públicas `imagem` e
`rpdf`.
