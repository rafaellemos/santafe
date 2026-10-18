# SLS — Servidor de Linguagem Santafé

O SLS roda localmente, como processo filho do editor, e conversa pelo protocolo
LSP (JSON-RPC 2.0 sobre entrada e saída padrão). Ele não abre porta de rede,
não executa o código editado nem envia o fonte a terceiros.

## Perfil estável inicial

O perfil inicial atende `initialize`, `shutdown` e o ciclo completo de documento:

- `textDocument/didOpen`;
- `textDocument/didChange` com sincronização integral;
- `textDocument/didSave`;
- `textDocument/didClose`.

Em cada abertura, alteração ou salvamento, o SLS chama `carregue` com o texto
recebido. Assim ele usa exatamente o analisador sintático do núcleo Santafé sem
executar o programa. Erros são devolvidos ao editor como diagnósticos LSP na
linha correspondente.

## Uso pelo editor

Após a instalação, o comando é:

```text
santafé-sls
```

O cliente do editor deve iniciá-lo por `stdio`; não use TCP nem acrescente
argumentos que produzam texto em `stdout`, pois essa saída pertence integralmente
ao protocolo LSP. O SLS anuncia codificação de posição `utf-16`, a convenção
esperada pelo VS Code e por clientes LSP compatíveis.

### VS Code

O cliente do VS Code fica em
[`extensões/vscode`](../extensões/vscode). A extensão 1.0.1 reconhece arquivos
`.fé` e `.fe`, aplica realce, trechos e regras básicas de edição, oferece
conclusões das palavras da linguagem e da API pública, ajuda rápida, estrutura
de funções e navegação para funções declaradas no arquivo aberto. Ela inicia
`santafé-sls` automaticamente para publicar os diagnósticos.

Empacote a extensão com:

```bash
cd extensões/vscode
python3 empacotar.py
```

Instale o arquivo gerado em `dist/` pela opção **Extensions: Install from
VSIX...** do VS Code. O comando `santafé-sls` precisa estar disponível na
mesma máquina em que o VS Code executa a extensão. Em uma sessão Remote SSH,
isso significa o computador remoto, não o computador local. Para uma compilação
local do próprio repositório, basta `make cbin`: a extensão usa automaticamente
`src/santafé` com `ferramentas/sls/sls.fé`. Para outros projetos, use
`make cbin ibin isls` para instalar o inicializador `santafé-sls`.

### Sublime Text

O pacote oficial está em [`extensões/sublime`](../extensões/sublime). Ele
reconhece `.fé` e `.fe`, fornece realce, snippets, conclusões da API pública,
ajuda curta e os comandos de execução e verificação sintática em
**Tools → Build System**.

O Sublime Text não traz um cliente LSP. Execute **Santafé: Ativar diagnósticos
SLS** para configurar o iniciador e solicitar o cliente **LSP** ao Package Control.
A configuração manual de exemplo continua disponível. Assim como no VS Code, `santafé-sls` deve estar disponível no `PATH`
do processo do editor.

## Limites atuais

O SLS ainda não tem análise semântica: conclusões que compreendam variáveis,
tipos, importações e funções entre arquivos, referências globais, formatação e
depuração pertencem às próximas etapas. As ajudas básicas da extensão são
deliberadamente locais e derivadas do manifesto da API pública; elas não fingem
conhecer tipos nem escopos entre arquivos. O diagnóstico sintático já estabelece
o processo, o contrato LSP e a suíte de integração para essas evoluções.

## Segurança e capacidade

Cada quadro LSP é limitado a 16 MiB. O SLS não avalia o documento: `carregue`
somente o compila. Como toda análise é local e cada mudança substitui o texto
anterior do documento, o processo não mantém cópias desnecessárias de versões
antigas.
