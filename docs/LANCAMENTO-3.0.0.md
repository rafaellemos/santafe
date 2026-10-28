# Santafé 3.0.0

Publicada em 27 de outubro de 2026 e registrada no Git em 28 de outubro de 2026.

## Componentes

- núcleo Santafé 3.0.0;
- SLS 1.1.0;
- gerenciador de bibliotecas 1.1.0;
- extensões VS Code e Sublime Text 2.0.0;
- IBA 3 e formato de bytecode da linha 3;
- pacotes para macOS, Debian GNU/Linux e Windows x64.

## Integridade e validação

O arquivo `MANIFESTO-FONTES.json` registra os 920 arquivos do pacote de fontes
publicado. O teste `testes/integracao/testar_registro_3_0.py` confere os fontes
de execução do Git contra esse manifesto e a coerência do SDK e dos editores.

Antes do registro foram aprovados: compilação, regressão completa, manual,
SLS, gerenciador, persistência ONFÉ, IBA, editores, WebAssembly, instalação e
reversão. No Windows 10/11 foram verificados console Unicode, VS Code, Sublime,
MSI, atualização, reparação, reversão e execução como usuário padrão.

O publicador definitivo também foi ensaiado contra uma réplica integral dos
oito aplicativos e dois bancos, preservando as imagens antigas dos processos e
sem modificar a produção durante o ensaio.

## Limites declarados

- o MSI não possui assinatura Authenticode pública;
- a validação auditiva por leitor de tela foi adiada;
- bibliotecas nativas precisam ser recompiladas para IBA 3;
- bytecode 2.1 não é executado pela linha 3;
- os downloads publicados são imutáveis; reconstruções locais não substituem
  os hashes expostos pelo portal.
