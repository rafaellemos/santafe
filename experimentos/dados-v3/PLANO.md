# Candidato dados.3 — migração e plataformas

Somente laboratório. Não instalar, publicar, reiniciar serviços, criar etiqueta
ou alterar os bancos/depósitos das empresas. Dados.2 permanece preservado.

## Critérios

- Fontes de bibliotecas e testes em árvore separada; migração léxica pelo núcleo
  estável, alterações semânticas explícitas e relatório reproduzível.
- Exclusão de caches/filas com `tabela.apague`; não transformar toda atribuição
  nula em exclusão, nem toda tabela numérica em lista por heurística.
- Recompilar os cinco módulos C. Rejeitar módulos com ABI antiga. Caminhos do
  laboratório sem fallback para módulos da instalação.
- PULSO/JSON preservam listas vazias, nulos e objetos; SQL preserva NULL em todas
  as posições, inclusive consultas preparadas.
- Executar ensaios locais e Debian; eventual MariaDB só em diretório temporário
  com configuração independente, sem acessar a instância de produção.
- WebAssembly compilado com o mesmo contrato e ensaiado pela ponte do portal.
  O teste Node com DOM mínimo não equivale a uma conferência visual de navegador.
- Registrar falhas e ensaios não executados. Candidato não implica versão estável.

## Estado inicial — 23/10/2026

Dados.2 validado em macOS. Debian 12.15 acessível; compilador, GLib, MariaDB
Connector, libsodium, OpenSSL e Emscripten 6.0.12 disponíveis. Nenhum pacote foi
instalado. Auditoria identificou exclusões por atribuição nula, tabelas que
atravessam JSON e linhas SQL com NULL como pontos explícitos de migração.

## Etapa concluída — 23/10/2026

Árvore migrada isoladamente e cinco módulos C recompilados. Em macOS e Debian:
76 testes de bibliotecas, 12 testes em MariaDB próprio, 39 testes adversariais
SLS e 39 de aceitação LSP passaram, além de ABI e fronteiras PULSO/JSON.
WebAssembly: 15 casos e recuperação após erro aprovados. Núcleo/ONFÉ: 10 testes
no Mac (com sanitizadores), 7 independentes do controle estável no Debian.
Evidências, correções e limitações detalhadas em `RELATORIO.md`.

Próxima ação: homologar a cadeia integral de aplicativos/ferramentas em ambiente
paralelo; repetir UI dos editores e fechar os demais gates da versão maior.
Não confundir a migração léxica de fontes com homologação integral. Produção
não alterada; não há comando de publicação em produção neste candidato.
