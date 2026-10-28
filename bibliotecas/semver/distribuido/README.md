# semver 1.0.0

Fontes distribuídos no TAR Santafé 2.1.0 do portal oficial, incluindo
`ferramentas/pacotes/versoes.fé` e a licença. O catálogo e esse TAR serão
publicados juntos, sem depender de uma etiqueta GitHub ainda não criada.

Versões semânticas em Santafé. Sem dependências, rede ou código nativo.
Licença MIT; Rafael Alves Lemos. O mesmo analisador é usado pelo gerenciador
de bibliotecas, com testes no repositório do núcleo.

```santafé
local versões = importe "semver"
garanta(versões.compare("1.2.0", "1.1.9") == 1)
garanta(versões.satisfaz("1.2.3", "^1.0.0"))
garanta(não versões.satisfaz("2.0.0", "^1.0.0"))
```

- `leia(texto)`: tabela da versão ou `nulo, diagnóstico`.
- `compare(a, b)`: `-1`, `0`, `1`; argumentos são textos ou tabelas de `leia`.
  Texto malformado gera erro; valide entradas externas com `leia` primeiro.
- `intervalo(texto)`: representação analisada ou `nulo, diagnóstico`.
- `satisfaz(versão, intervalo)`: lógico; texto inválido gera erro. Pode receber
  as representações já verificadas por `leia` e `intervalo`.

SemVer com três componentes, pré-lançamento e metadados. Componentes principais
até 2.147.483.647. Metadados não alteram precedência. Intervalos aceitam exato,
`^`, `~`, comparadores separados por espaços, alternativas `||`, versões parciais
e curingas `x`, `X`, `*`. Não há intervalo com hífen (`1.0.0 - 2.0.0`).
Pré-lançamentos exigem comparador de pré-lançamento no mesmo núcleo numérico.
Não normaliza nem completa automaticamente versões malformadas.

Esta biblioteca é código Fé e só executa quando importada pelo seu programa.
O comando de instalação não a executa.
