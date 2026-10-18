# API pública das bibliotecas Fé

Este documento define a fronteira entre contratos estáveis e detalhes de
implementação das bibliotecas escritas em Fé.

## Regra

O arquivo [`API-PUBLICA-FE.tsv`](API-PUBLICA-FE.tsv) é o manifesto normativo.
Cada linha associa o nome apresentado no manual ao arquivo que o implementa.
Somente os contratos presentes nesse manifesto fazem parte da API pública.

Símbolos, campos e módulos auxiliares não listados são internos por padrão.
Podem mudar sem promessa de compatibilidade, ainda que hoje possam ser
alcançados por inspeção da tabela devolvida pelo módulo.

## Módulos deliberadamente internos

- `imagem_png`, `imagem_jpeg` e `imagem_svg`: implementam formatos para a
  fachada pública `imagem`;
- `rpdf_unicode`: implementa fontes e codificação para a fachada pública
  `rpdf`;
- funções locais, nomes iniciados por sublinhado e métodos do adaptador
  MariaDB não promovidos pelo manifesto;
- detalhes das aplicações completas em `aplicativos/`, que não são
  bibliotecas da linguagem.

`correio.multibanco` e `correio.transporte` são exceções deliberadas: sua
superfície listada é pública porque compõe implantações escaláveis com bancos
isolados e transporte SMTP substituível. Isso não torna pública a configuração
particular de nenhuma empresa ou domínio.

## Porta de qualidade

`site-sfdev/validar-manual.py` confere simultaneamente que:

1. cada contrato do manifesto continua documentado;
2. o arquivo declarado continua presente;
3. o nome final do contrato continua declarado pelo fonte;
4. a API C registrada em `luaL_Reg` também permanece documentada.

Uma retirada ou renomeação pública deve atualizar fonte, manifesto, manual,
testes e histórico na mesma alteração. Acrescentar um auxiliar interno não
exige ampliar a API pública.
