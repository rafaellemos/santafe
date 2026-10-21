# Santafé 2.0.3 — manutenção da linha 2.0

Preparação: 20 de outubro de 2026 (America/Sao_Paulo).
Sem funcionalidades novas, novos comandos LSP ou alterações de ABI.

## Correções e evidência

- `974add3`: a fixture HTTP do Carteiro não presume o fuso de Brasília.
  A regressão executa em UTC, America/Sao_Paulo e Asia/Tokyo.
- `fb11631`: a RPDF procura a fonte Noto Sans ao lado do módulo carregado,
  inclusive em instalações com prefixos personalizados. `RPDF_FONTE` conserva
  sua precedência. O teste exige a fonte da instalação ensaiada e gera um PDF,
  evitando sucesso falso provocado por outra instalação em `/usr/local`.
- O publicador ajusta o `prefix` do `pkg-config` ao destino definitivo.
  Na preparação desta entrega, o metadado instalado ainda apontava para a
  pasta temporária usada no ensaio da 2.0.2. A regressão agora exige que o
  prefixo corresponda à instalação, inclusive após a troca em `/usr/local`.

As duas correções passaram integralmente no
[GitHub Actions — Ubuntu 24.04 e macOS 14](https://github.com/rafaellemos/santafe/actions/runs/39529884537).
Essa execução testou `fb11631`, não a etiqueta antiga nem o empacotamento
posterior 2.0.3. O lançador de manutenção repete compilação, regressões,
instalação isolada, testes de editores, manual e WebAssembly antes da troca.

## Identidade da entrega

- Núcleo, compilador, distribuição e executor WebAssembly: 2.0.3.
- SLS: 0.1.1; VS Code: 1.0.6; Sublime: 1.0.13, sem alterações.
- ABI C: 503; layout de bibliotecas: `santafé/1.0`, preservados.
- A etiqueta prevista é `v2.0.3`, a registrar somente após a publicação.
  O manifesto não declara uma etiqueta existente antes desse registro.
- `v2.0.2`, `v2.0.2-r2` e seus artefatos permanecem intactos. Novos arquivos
  usam nomes 2.0.3 e a guarda de imutabilidade recusa substituí-los por conteúdo
  diferente se essa versão já tiver sido publicada.

## Escopo operacional

O publicador atualiza núcleo, compilador, SLS, cabeçalhos C, metadado pkg-config,
manual, página de downloads e WebAssembly. Instala também **somente**
`rpdf_unicode.fé` e o LEIA-ME da RPDF entre as bibliotecas operacionais.
Não troca bibliotecas C, Correio, bancos, configurações empresariais ou segredos.
Os pacotes dos editores são comparados com os públicos, sem republicação.

O fonte público exato fica em `/home/rafael/santafe-fonte/versoes/2.0.3`;
o executor fica em `/estático/wasm/2.0.3/`. Caminhos históricos permanecem
disponíveis. A cópia de segurança registra os arquivos alterados e permite
restauração; em caso de falha, a troca é revertida automaticamente.

Somente `sfdev.service` é reiniciado. Os demais processos persistentes não são
reiniciados e conservam módulos já carregados até sua próxima manutenção.
Pão do Café continua sendo uma implantação independente.

## Publicação

Após conferir os pacotes e o lançador em `/tmp`:

```sh
sudo bash /tmp/publicar-fechamento-santafe-2.0.3.sh
```

Para repetir apenas a pré-validação, sem sudo, instalação ou reinício:

```sh
bash /tmp/publicar-fechamento-santafe-2.0.3.sh --preflight
```

Somente a conclusão do modo de publicação confirma a instalação em produção.
Os testes MariaDB que exigem credenciais são ignorados na suíte geral quando
essas variáveis não estão presentes; não equivalem a uma nova homologação dos
bancos operacionais. Windows e interação gráfica com editores não são
revalidados por esse publicador; os editores não mudaram nesta manutenção.
