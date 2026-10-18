# Santafé 2.0.1

Santafé 2.0.1 é uma correção de instalação para a linha estável 2. Não altera
a sintaxe, o vocabulário público, a ABI C, as bibliotecas nem o SLS 0.1.0.

## Correção

O instalador passou a exibir cada fase no próprio terminal. Nas versões
anteriores uma animação baseada em `sleep` escondia a cadeia de dependências,
compilação e cópia; se o gerenciador de pacotes, a rede ou o compilador
aguardasse algo, o processo parecia travado sem informar a etapa responsável.

O fluxo guiado também não repete mais a preparação das dependências pelo
`make`, nem executa o Homebrew com privilégios de root. O código é compilado
como o usuário corrente e somente as cópias em `/usr/local` pedem `sudo`.

## Instalação

```bash
chmod +x instalar.sh
./instalar.sh
```

O instalador mostra claramente a ação em andamento e conserva as mensagens de
erro do compilador e do gerenciador de pacotes.

## Compatibilidade

O contrato permanece compatível com Santafé 2.0.0. Para a migração da linha
1.0, consulte [MIGRACAO-VOCABULARIO-LOGICO.md](MIGRACAO-VOCABULARIO-LOGICO.md).
