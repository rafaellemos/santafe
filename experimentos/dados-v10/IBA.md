# IBA 3 — contrato do candidato dados.10

IBA significa Interface Binária de Aplicação (ABI). A identidade escolhida
para a próxima versão maior é `santafe-3`. Esta decisão não promove o candidato
nem autoriza misturar bibliotecas com a instalação estável 2.1.

## Carregamento e SDK

Cada biblioteca compartilhada recompilada declara `SANTAFE_MODULE_ABI;` em
exatamente uma unidade de tradução, depois de incluir `lua.h`/`lauxlib.h`
(ou `lua.hpp` em C++). O SDK candidato precisa da definição
`SANTAFE_DADOS_EXPERIMENTAL`; o arquivo `santafe.pc` instalado a fornece.
Não use cabeçalhos ou objetos das versões 2.x, Lua ou dados.9.

O descritor público contém magic, comprimento, época, tamanhos do ponteiro,
inteiro e número, modalidades numéricas, área extra do estado e limite de pilha.
O carregador o confere antes de devolver o inicializador `luaopen_*`, inclusive
na modalidade de símbolos globais. A checagem independe de o módulo chamar
`luaL_checkversion`. Essa segunda checagem continua existindo e também separa
as épocas. Bibliotecas embutidas/estáticas são recompiladas junto do núcleo.

Isto detecta incompatibilidades acidentais; não é isolamento de código nativo.
`dlopen`/`LoadLibrary` já pode executar construtores. Uma biblioteca maliciosa
pode falsificar o descritor. Só carregue bibliotecas nativas confiáveis.

A API C conserva nomes e `LUA_VERSION_NUM = 503` por herança da base; esse
número não identifica a IBA. Listas usam `LUA_TTABLE` na API C e são reconhecidas
por `lua_islist`; `lua_createlist` cria uma lista. O formato interno de estados,
valores e tabelas é privado. Atribuir nulo guarda a associação; exclusão é
explícita. Código C que antes usava nil para apagar precisa ser migrado também.

O gerenciador inclui `iba = "santafe-3"`, `bytecode = 48` e a cerca numérica
`abiDados` na identidade da plataforma. Caches nativos anteriores não servem
como substitutos dos módulos recompilados.

## Bytecode

A assinatura é `1b 53 46 33` (ESC SF3), versão de formato `0x30`, formato `0`.
Núcleos 2.1 e IBA3 recusam reciprocamente seus bytecodes. Dados.9 também é
recusado. Tamanhos e representações numéricas continuam sendo conferidos pelo
leitor. Bytecode é específico da instalação/arquitetura, não um formato
portátil ou seguro para dados externos. Distribua fontes para recompilar.

## Critérios e limites

`testar-iba.py` verifica módulos corretos, ausência de descritor mesmo sem
checkversion, época/números incorretos, descritor curto, visibilidade oculta,
carga repetida/global, SDK instalado C/C++ em prefixo com espaços, bytecode
normal/sem depuração, 36 cabeçalhos inválidos e identificação do gerenciador.
Os resultados devem ser consultados por plataforma: não presumir Windows,
ARM ou WebAssembly pelo resultado macOS/Debian. WebAssembly não usa DSOs.

A promoção estável ainda exige a réplica operacional completa, revisão das
migrações semânticas, preservação de bancos/depósitos/filas e reversão compatível
com mensagens recebidas depois da atualização. Os ensaios sintéticos e as
trocas atômicas de executáveis isolados não satisfazem esse requisito sozinhos.
