# Santafé para Visual Studio Code

Extensão Santafé 1.0.1 para arquivos (`.fé` e `.fe`). Ela oferece:

- reconhecimento de arquivos, comentários, pares e indentação;
- realce de sintaxe, trechos e ícone próprio;
- conclusões para a linguagem, bibliotecas, funções globais, API pública e
  símbolos declarados no arquivo atual;
- ajuda ao passar o mouse, estrutura de funções no explorador e navegação para
  funções declaradas no arquivo atual;
- diagnósticos sintáticos em tempo real através do SLS.

Salve o arquivo com a extensão `.fé` ou `.fe` — ou escolha **Santafé** no
seletor de linguagem do canto inferior direito — para ativar esses recursos.

## Instalação

O SLS é um processo local. Instale o núcleo Santafé na mesma máquina onde o
VS Code está rodando, de forma que `santafé-sls` esteja no `PATH`. Em uma sessão
Remote SSH, esse comando deve estar instalado no host remoto da extensão.

Ao abrir o próprio repositório Santafé, a extensão encontra automaticamente
`src/santafé` e `ferramentas/sls/sls.fé`. Basta compilar o núcleo:

```sh
make cbin
```

Para trabalhar em qualquer outro projeto, instale o inicializador global:

```sh
sudo make install
```

Gere o pacote sem depender de Node.js:

```sh
python3 empacotar.py
code --install-extension dist/santafe-1.0.1.vsix
```

Também é possível escolher **Instalar do VSIX...** na visualização Extensions do
VS Code e selecionar o arquivo gerado.

## Configuração

Por padrão a extensão executa:

```text
santafé-sls
```

Para apontar a outra instalação, defina `santafe.languageServer.command` nas
configurações do VS Code. `santafe.languageServer.args` acrescenta argumentos
ao comando. Use `santafe.languageServer.trace` para inspecionar os quadros LSP
em **Saída → Santafé SLS**.

## Limites da versão 1.0.1

O SLS atual analisa sintaxe no conteúdo aberto, alterado ou salvo e não executa
o programa. As conclusões e a navegação desta extensão são locais; referências,
tipos, importações e definição entre arquivos, formatação e depuração dependem
de uma análise semântica futura do SLS.
