# Bateria Windows nativa — dados.15

Estado: **em homologação no Windows**. A primeira execução compilou o núcleo e
identificou falhas Unicode; a correção passou 21 verificações. O ensaio de DLLs
está em andamento. O usuário informou que
não dispõe de máquina Windows. A alternativa preparada é um executor
`windows-2022` do GitHub Actions, com compilador UCRT64 e Python Windows nativos.
MSYS2 fornece o ambiente de construção; o teste recusa executáveis dependentes
de `msys-2.0.dll` ou `cygwin1.dll`. WSL/Wine não contam como homologação nativa.

## Alteração concreta para revisão

Ramo temporário proposto: `homologacao/windows-dados15`, no repositório
`rafaellemos/santafe`. Árvore independente: fonte selada `fonte.tar.gz`, os
auxiliares desta pasta e `.github/workflows/homologacao-windows.yml`.
Sem credenciais, ambientes de produção, deploy, etiquetas ou alteração do ramo
principal. Workflow com `contents: read`, sem persistir a credencial do checkout,
limite de 30 minutos e evidências guardadas por 14 dias.

O usuário autorizou explicitamente o ramo temporário e os testes Windows.
Essa autorização não abrange produção, publicação estável ou etiquetas.

## Escopo da primeira execução

1. Conferir SHA-256 da fonte selada e seus 869 arquivos antes da alteração.
2. Corrigir isoladamente o alvo MinGW: retirar `rcu` duplicado; compilar
   interpretador e compilador com a mesma biblioteca e opções.
3. Compilar a variante estável e a candidata; conferir formato PE x86_64,
   ausência de dependência de emulação POSIX e versão.
4. Executar listas, nulos, gabaritos Unicode, grafemas, JSON e ONFÉ em memória.
5. Ensaiar a IBA C estática, DLLs sintéticas e a recusa cruzada de bytecode
   estável/candidato. DLL atual deve preservar listas/nulos; DLLs sem descritor,
   de outra época ou com descritor curto devem ser recusadas.
6. Exercitar caminhos com espaços/Unicode e argumentos Unicode reais.

Mesmo todos esses testes passando, o resultado será `passou_escopo_parcial`.
Não aprova a versão maior nem anuncia suporte completo ao Windows.

## Trabalho de portabilidade ainda necessário

- O Makefile principal pula os módulos nativos de SLS e gerenciador no MinGW.
- SLS usa descritores, `openat`, `O_NOFOLLOW`, diretórios e espera POSIX.
- Gerenciador usa processos, limites, bloqueios e operações relativas a
  descritores POSIX. Portar para Win32 preservando confinamento, recusa de
  reparse points e integridade; não remover controles para fazer compilar.
- Integrar DLLs e testar a IBA dinâmica, dependências e caminho Unicode.
- Implementar/testar lançadores e instalação, atualização e reversão nativas.
- Homologar persistência ONFÉ atômica em NTFS e integrações dos editores.

O alvo padrão do núcleo é estático. O ensaio constrói separadamente um núcleo
DLL e uma biblioteca de importação para testar a IBA; isso ainda não é um SDK
Windows completo instalado. O diagnóstico de compilação será usado para orientar
as próximas correções. A produção continua fora desse percurso.

## Verificações locais executadas

Preparação/hash, recusa de arquivo corrompido/destino existente, comandos de
compilação por `make -n`, sintaxe Python, contrato Fé e sonda C estática foram
verificados no macOS. A bateria recusa execução no macOS e não gera um resultado
Windows falso. Evidências em `../evidencias/preparacao-windows.json`.

Documentação do ambiente: <https://www.msys2.org/docs/ci/> e
<https://www.msys2.org/docs/environments/>.

## Correção Unicode

O processo passa a declarar `activeCodePage=UTF-8` em manifesto embutido nos
executáveis. A página de códigos do sistema não é alterada. Esse mecanismo
exige Windows 10 1903+; a execução atual usa Windows Server 2022, sem alegar
ensaio de todas as versões Desktop. Fonte oficial:
https://learn.microsoft.com/en-us/windows/win32/sbscs/application-manifests#activecodepage

A primeira execução foi preservada com suas falhas. A compilação e a IBA estática
passaram; `onfé.fé` não era localizado pelo CRT e o caminho com Unicode chegava
corrompido. O logger Python foi separado desse defeito e agora grava Unicode
sem falhar ao apresentar os próprios diagnósticos. Bytes de saída são preservados.

O linker MinGW/GCC usado pelo executor falhou ao gravar DLLs em diretório com
ideogramas. As sondas são compiladas em caminho ASCII e copiadas para
`módulos-漢字`, onde o interpretador candidato tenta carregá-las. Esta adaptação
não remove o teste Unicode do carregador e não declara suporte Unicode do GCC.
