# Bateria Windows nativa — dados.15

Estado: **preparada, ainda não executada no Windows**. O usuário informou que
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
5. Ensaiar a IBA C estática e a recusa cruzada de bytecode estável/candidato.
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

O alvo atual do núcleo é estático; este ensaio não mascara a ausência de um SDK
dinâmico Windows completo. O diagnóstico de compilação será usado para orientar
as próximas correções. A produção continua fora desse percurso.

## Verificações locais executadas

Preparação/hash, recusa de arquivo corrompido/destino existente, comandos de
compilação por `make -n`, sintaxe Python, contrato Fé e sonda C estática foram
verificados no macOS. A bateria recusa execução no macOS e não gera um resultado
Windows falso. Evidências em `../evidencias/preparacao-windows.json`.

Documentação do ambiente: <https://www.msys2.org/docs/ci/> e
<https://www.msys2.org/docs/environments/>.
