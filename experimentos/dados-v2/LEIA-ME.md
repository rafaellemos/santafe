# Candidato dados.2 — núcleo, ONFÉ e SLS integrados

Laboratório **macOS x86_64**, não uma versão de produção. O executável, o SLS `1.0.0-dados.2` e os editores têm identidades separadas. Não instale este núcleo sobre Santafé 2.1.0 e não o use para executar aplicações reais sem migração.

## Experimentar

Na raiz do pacote extraído ou deste repositório, sem `sudo`:

```sh
sh experimentos/dados-v2/experimentar.sh
sh experimentos/dados-v2/experimentar.sh testar
```

O segundo comando repete os testes de núcleo/ONFÉ/migração, os adversariais SLS e o contrato LSP. Os executáveis de candidato e controle estão incluídos. Python 3 é necessário para a bateria; nenhuma dependência é baixada.

Para um programa de teste próprio:

```sh
sh experimentos/dados-v2/experimentar.sh /caminho/absoluto/ensaio.fé
```

Esse comando **executa** o programa indicado; use somente fontes de confiança. `.onfé` é dado: carregue por `importe "onfé"` e `onfé.carregue(caminho)`, nunca por `executeArquivo`.

## Editores isolados

`python3 experimentos/dados-v2/preparar-hosts.py` cria um novo projeto temporário com exemplos públicos, perfil VS Code e configuração Sublime. Mostra o caminho criado. Não instala extensões ou modifica preferências existentes.

- **VS Code:** o kit está em `dist/candidato-dados-v2/editores/vscode`, com VSIX experimental `santafe-dados-experimental-0.0.2.vsix`. Use o perfil temporário com `--extensionDevelopmentPath` ou instale o VSIX somente nesse perfil. Selecione **Santafé Dados Experimental** para `.fé`. Configure `santafeDados.languageServer.command` como `/bin/sh` e `santafeDados.languageServer.args` com o caminho absoluto de `experimentos/dados-v2/santafe-sls-dados`.
- **Sublime:** `SantafeDados.sublime-package` é separado de `Santafe.sublime-package`. Requer o cliente **LSP** já instalado para os recursos de linguagem; o realce básico não depende dele. Abra o projeto temporário `dados.sublime-project`, que habilita somente o SLS candidato nessa janela. Selecione a sintaxe experimental. O arquivo `LSP-santafe-dados.sublime-settings.example` é um exemplo, não configuração global automática.
- Ambos: listas e colares brutos, `®`/`Ⓡ` com Unicode, código dentro dos gabaritos, HTML/JS através de concatenações e paleta suave. ONFÉ tem realce e diagnósticos de dados; não oferece rename, formatação nem conclusões estruturadas de dados nesta etapa.

Os testes reais estão em `testar-host-vscode.js` e `Homologacao.py`. Só aceitam uma pasta chamada `santafe-dados2-host-*`; modificam buffers de exemplos, sem salvar. O comando Sublime de laboratório é `santafe_dados_homologue`. Não execute esse comando em seus projetos.

## Declarações e nulo

Não existe `temVar`. `local var` declara a variável e inicializa com nulo; `var=nulo` não desfaz a declaração. Em condição, nulo é falso. Nas tabelas, `tabela.temChave` distingue presença e ausência; `tabela.apague` exclui explicitamente.

O SLS oferece o aviso opcional `initializationOptions.avisosEscopo=true` para nomes sem declaração local visível. No VS Code experimental: `santafeDados.languageServer.scopeWarnings`. No Sublime: `initializationOptions` do cliente no projeto. O aviso não é erro de execução nem afirmação de que um global dinâmico não existe. Os projetos de laboratório ativam esse aviso; o padrão do servidor continua desligado.

## Reconstrução e isolamento

```sh
sh experimentos/dados-v2/construir.sh
sh experimentos/dados-v2/construir.sh estavel
sh experimentos/dados-v2/construir.sh sanitizado
python3 experimentos/dados-v2/editores.py
```

Compilador C e `make` são necessários. Construções usam diretórios temporários novos, preservam os objetos e binários do checkout e não habilitam carregamento de módulos C da produção. O suporte nativo mínimo do SLS é vinculado ao próprio executável, com a mesma ABI. O SHA-256 embutido desta construção usa CommonCrypto no macOS; Linux/Windows/WebAssembly ainda exigem homologação explícita.

Para os testes de gramática/camadas embutidas no Mac, pode-se usar o Node do VS Code, sem instalar pacotes:

```sh
ELECTRON_RUN_AS_NODE=1 '/Applications/Visual Studio Code.app/Contents/MacOS/Code' \
  experimentos/dados-v2/testar-editores.js \
  '/Applications/Visual Studio Code.app/Contents/Resources/app'
```

O pacote contém um manifesto ONFÉ com SHA-256 por arquivo e um `SHA256SUMS` do arquivo compactado. A remoção do candidato consiste em remover apenas a pasta extraída/perfis de laboratório e desinstalar a extensão experimental. Nenhum serviço é instalado.

## Ainda não é uma versão maior liberada

Faltam a migração do ecossistema/bibliotecas, ABI C definitiva, SQL/rede, matriz Debian/Windows/WebAssembly, desempenho de produção, escrita atômica ONFÉ e ponte JSON etiquetada para mapas de chaves não textuais. Listas ainda não recebem metatabelas. O contrato e o relatório discriminam os limites; não são convertidos em aprovações por estes testes locais.

Veja `docs/CONTRATO-DADOS-ONFE.md` e `experimentos/dados-v2/RELATORIO.md`. O manual público, downloads e serviços não foram alterados.
