# Fontes das DLLs externas — candidato dados.20

Incluídos os pacotes de fontes MSYS2 completos das quatro DLLs distribuídas:
GLib, libiconv, GNU gettext (libintl) e PCRE2. Cada arquivo .src.tar.zst contém
PKGBUILD, .SRCINFO, o arquivo original do projeto e as adaptações da distribuição.
As assinaturas .sig e um lock com SHA-256 acompanham os arquivos. A construção
confere assinaturas com o chaveiro MSYS2 e recusa versão/hash de DLL divergentes.

Os avisos de licença aplicáveis estão em LICENCAS-TERCEIROS e nos fontes. A
Santafé não é autora dessas bibliotecas. A aplicação usa suas DLLs dinamicamente;
a licença MIT da Santafé não substitui as licenças dos componentes de terceiros.

Para estudar ou reconstruir uma biblioteca, extraia o respectivo pacote de
fontes em uma área isolada, examine PKGBUILD/.SRCINFO e suas dependências e use
um ambiente MSYS2 UCRT64 com makepkg-mingw. A receita e patches são os originais
MSYS2, preservados aqui. Construção executa código: não é feita pelo instalador.
Não execute receitas de origem desconhecida ou com privilégios de administrador.

Estas DLLs são arquivos separados no diretório bin e podem ser substituídas por
uma versão compatível reconstruída pelo usuário; nenhuma assinatura Santafé foi
aplicada a elas. Alterações deixam de corresponder aos hashes da homologação e
uma reparação/atualização MSI restaura os arquivos originais. Guarde sua versão
modificada antes desses procedimentos. Os testes de integridade avaliam o pacote
original; não constituem uma proibição de estudar ou modificar as bibliotecas.

O lock cobre as quatro DLLs redistribuídas e seus fontes, não todas as ferramentas
do ambiente de construção. AMBIENTE-CONSTRUCAO.txt registra as versões usadas.
Isso não promete reprodução binária byte a byte. Para publicação estável, oferecer
este conteúdo junto dos binários e preservar seus avisos, instruções e licenças.

Fontes oficiais:
- https://repo.msys2.org/mingw/sources/
- https://www.msys2.org/docs/package-management/
- https://www.msys2.org/wiki/Creating-Packages/
