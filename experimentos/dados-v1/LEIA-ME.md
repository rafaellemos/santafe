# Candidato experimental de listas nulos e ONFÉ

Este candidato é um executável paralelo para homologar o contrato de dados. Não instala nem substitui a Santafé 2.1.0, o SLS ou as extensões atuais. Não execute aplicações reais nele: atribuições nulas e colares longos mudaram de significado.

## Experimentar no Mac

Na raiz deste repositório:

```sh
sh experimentos/dados-v1/experimentar.sh
sh experimentos/dados-v1/experimentar.sh testar
```

O primeiro comando executa um exemplo de listas, nulo presente, exclusão, gabaritos, texto bruto e ONFÉ/JSON. O segundo executa a bateria automatizada. Não há acesso a produção, rede, banco ou credenciais.

Para usar um arquivo próprio, forneça seu caminho absoluto:

```sh
sh experimentos/dados-v1/experimentar.sh /caminho/absoluto/teste.fé
```

Nesse lançador, `importe "onfé"` encontra o módulo experimental. Dados são lidos com `onfé.carregue("arquivo.onfé")`, nunca com `executeArquivo`. O exemplo utiliza caminho explícito para o módulo de modo a também funcionar na bateria direta do executável.

## Reconstruir

```sh
sh experimentos/dados-v1/construir.sh
sh experimentos/dados-v1/construir.sh sanitizado
sh experimentos/dados-v1/construir.sh estavel
```

São necessários compilador C e `make`. Cada construção usa um diretório temporário novo e preserva os arquivos `src/*.o` e `src/santafé` existentes. Os modos adicionais geram diretórios separados para sanitizadores e para verificar a compilação estável sem a opção experimental. O script não usa `sudo` e não tem etapa de instalação. A bateria cruzada também usa Python 3 e o núcleo estável em `src/santafé`; pode apontá-lo com `SANTAFE_ESTAVEL`.

O pacote contém o executável macOS testado e os fontes para reconstrução. Não use o binário macOS em Debian. A compilação e os testes Debian, Windows e WebAssembly ainda são pendências desta experiência.

## Migrar um exemplo antigo

```sh
src/santafé -E -P experimentos/dados-v1/migrar.fé /caminho/exemplo-antigo.fé
```

O comando só mostra o fonte convertido na saída padrão e avisos na saída de erro. Não sobrescreve nada. Ele converte colares longos pelos lexemas, inclusive o antigo gabarito vazio, mas **não decide** quais tabelas devem virar listas nem quais atribuições de nulo devem virar exclusão. Isso exige revisar a intenção do programa.

## Editores

Os pacotes em `dist/candidato-dados-v1/editores` possuem identidade experimental e não substituem os publicados. No VS Code, instale o VSIX experimental e escolha manualmente a linguagem **Santafé Dados Experimental**. No Sublime, use o pacote experimental separado e escolha essa sintaxe. A sintaxe ONFÉ também é fornecida.

São gramáticas de laboratório, não as próximas versões definitivas das extensões. Não incluem ainda a camada completa de HTML/JS embutidos nem integração de todas as funções do SLS no novo dialeto. Testes de tokenização TextMate e leitura estrutural do YAML não substituem conferência visual no editor.

## SLS e limitações de promoção

`testar-sls.fé` verifica listas aninhadas, referências, recuperação de erro e intervalos em octetos no compilador/analisador. O modo novo é explícito no terceiro argumento de `A.analise` e não altera o padrão estável.

Não configure ainda o **serviço LSP completo** para executar no novo núcleo. Suas exclusões em caches, suas estruturas de mensagens JSON e seus módulos nativos precisam de migração. A sincronização incremental da versão estável não foi substituída por uma implementação reduzida neste candidato.

Também ficam para a próxima etapa: ABI C definitiva de lista, bibliotecas SQL e de rede, metatabelas de listas, JSON etiquetado para mapas de chaves nativas, escrita atômica ONFÉ, endurecimento completo de Unicode/binários, casos complexos de delimitação interna de gabaritos e testes de desempenho. Nenhum desses itens deve ser considerado concluído com os testes deste candidato.

O contrato completo está em `docs/CONTRATO-DADOS-ONFE.md`; os resultados executados estão em `RELATORIO.md` neste diretório.
