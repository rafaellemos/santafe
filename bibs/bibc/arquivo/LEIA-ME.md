# arquivo

Biblioteca C de entrada e saída assíncrona para Santafé. As operações de
disco são executadas fora do laço principal e o tratador retorna no contexto
GIO usado por `rede` e `mariadb`.

## API inicial

```santafé
arquivo = importe "arquivo"

arquivo.leiaAssíncrono(caminho, limite, tratador [, dado])
arquivo.graveDurávelAssíncrono(caminho, conteúdo, tratador [, dado])
arquivo.graveDurávelComPermissõesAssíncrono(caminho, conteúdo, permissões,
    tratador [, dado])
arquivo.movaAssíncrono(origem, destino, tratador [, dado])
arquivo.removaAssíncrono(caminho, tratador [, dado])
arquivo.crieDiretóriosAssíncrono(caminho, tratador [, dado])
arquivo.crieDiretóriosComPermissõesAssíncrono(caminho, permissões,
    tratador [, dado])
arquivo.existeAssíncrono(caminho, tratador [, dado])
```

Todos os tratadores recebem `(resultado, falha, dado)`. Conteúdos são
binários: tacos zero e UTF-8 são preservados sem transformação.
Cada chamada devolve `verdadeiro` quando a tarefa foi agendada; o resultado
real chega depois ao tratador. Uma aplicação independente precisa manter
`rede.laço()` ativo. Rede, Caminheiro, Correio e MariaDB já compartilham esse
mesmo contexto GIO.

Os caminhos podem ser absolutos ou relativos. A biblioteca rejeita caminho
vazio e taco zero interno, mas não cria uma caixa de areia: o consumidor deve
definir uma raiz permitida e não concatenar diretamente caminhos recebidos do
usuário.

`graveDurávelAssíncrono` escreve primeiro um arquivo temporário no mesmo
diretório, sincroniza seu conteúdo, renomeia atomicamente e sincroniza o
diretório. Um leitor nunca observa um arquivo parcialmente gravado. O arquivo
publicado recebe permissão `0600`: somente seu dono pode lê-lo ou alterá-lo.
As variantes `ComPermissões` recebem o modo POSIX em decimal. Por exemplo,
`432` equivale a `0660`, e `1528` equivale a `02770` (grupo compartilhado e
herança do grupo nos subdiretórios).

`crieDiretóriosComPermissõesAssíncrono` aplica o modo informado quando cria
o diretório. Se o caminho já for um diretório, suas permissões e seu dono são
preservados. Isso permite que serviços diferentes do mesmo grupo utilizem uma
árvore compartilhada sem que um deles tente alterar a propriedade do outro.

`movaAssíncrono` usa uma renomeação atômica e, por isso, origem e destino
devem pertencer ao mesmo sistema de arquivos. Em sistemas POSIX, um arquivo de
destino preexistente pode ser substituído. Essa operação não faz a
sincronização durável oferecida pela gravação. `removaAssíncrono` também
remove diretórios vazios, nunca remove uma árvore recursivamente e considera
sucesso a ausência do caminho pedido.

`leiaAssíncrono` exige um limite explícito ou usa 64 MiB. O limite evita que
um arquivo inesperado ocupe toda a memória do processo.

Esta primeira versão trabalha com conteúdos inteiros em memória. Ela resolve
as gravações duráveis do Correio sem bloquear o laço principal, mas ainda não
é a interface indicada para arquivos arbitrariamente grandes. Leitura e
escrita em fluxo, contrapressão e cancelamento ficam para a próxima etapa.
