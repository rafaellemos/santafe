# Bibliotecas Santafé — contrato do gerenciador e repositório 1.0

Versão **1.0.0, publicada e conferida em 21/10/2026**. O repositório de bibliotecas não é o GitHub
do núcleo nem o catálogo de extensões dos editores. O usuário instala pelo
comando `santafé instale nome`, dentro do projeto. Nenhuma instalação global
implícita e nenhuma execução de scripts recebidos durante resolução.

## Contrato de entrega

- Manifesto JSON do projeto, `santafe.json`; dependências por nome/intervalo.
- Resolução determinística de dependências transitivas, com conflitos,
  ciclos, limites e escolha explícita de prévias. Uma versão por pacote.
- `santafe.lock` com versões exatas, origem e SHA-256. Instalação travada
  recusa divergência; não escolhe silenciosamente uma atualização.
- Pacotes imutáveis e curados, catálogo estático HTTPS no portal oficial.
  A mesma versão nunca pode ser substituída por bytes diferentes.
- Integridade do pacote e de cada arquivo; nomes/caminhos confinados,
  ausência de links, travessia, dispositivos e scripts de pós-instalação.
- Instalação em geração privada do projeto, troca atômica de estado, trava
  entre processos, recuperação após falha e retenção da geração anterior.
- Cache de downloads verificados; modo sem rede usando o lock e o cache.
- Bibliotecas Fé não executadas na instalação. Bibliotecas C só compiladas
  com autorização explícita, receita declarativa e compilador local; nunca
  um comando de shell arbitrário vindo do pacote. Compilar não é sandbox de
  segurança: código nativo exige confiança e pode acessar recursos do usuário
  quando carregado. Nenhum `sudo` automático.
- Execução e SLS usam os módulos efetivamente resolvidos no projeto. O SLS
  não instala nem compila dependências durante análise.
- Administração do catálogo separada do cliente. A primeira versão é
  curada pelo mantenedor, sem upload público anônimo ou cadastro de contas.
  Fontes, licença e autoria devem acompanhar cada pacote.

## Uso

Instale a distribuição completa (`instalar.sh` ou `make instalar`). A instalação
mínima `make install` entrega núcleo/SLS, não todas as bibliotecas opcionais;
para acrescentar só o gerenciador a ela, use `make pacotes ipacotes` com o mesmo
`INSTALL_TOP`. O cliente precisa de GLib e `/usr/bin/curl`; C adicional precisa
de `/usr/bin/cc` e dos cabeçalhos Santafé. Não exige Python ou Node no uso normal.
Suporte inicial: macOS e Linux POSIX; Windows ainda não implementado/homologado.

```sh
mkdir meu-projeto
cd meu-projeto
santafé instale semver '^1.0.0'
santafé -e 'mostre((importe "semver").compare("1.2.0", "1.1.9"))'

# Em outro checkout do MESMO projeto, preservando origem/versões/hashes:
santafé instale --travado
# Sem rede, exige que todos os pacotes já estejam no cache desse projeto:
santafé instale --sem-rede
# Atualização dentro dos intervalos declarados, pedida explicitamente:
santafé instale --atualizar
```

O endereço oficial disponível é
`https://xn--santaf-gva.dev.br/est%C3%A1tico/bibliotecas/v1`.
O catálogo inicial contém `semver 1.0.0`. Para ensaios isolados, é possível usar
`--repositorio-local` apontando para um catálogo gerado localmente.
Outra origem HTTPS pode ser selecionada com `--repositorio URL`.
Ela precisa coincidir com a origem do lock. Endereços HTTP, credenciais na URL
e redirecionamentos para HTTP são recusados. Não existe opção para ignorar TLS;
`--autoridade-certificadora /caminho/ca.pem` é uma escolha explícita de confiança.

Os comandos operam no **diretório atual**, sem subir automaticamente aos pais.
Mantenha `santafe.json` e `santafe.lock` no Git; ignore `.santafe/`. O intérprete
reconhece a geração ativa ao iniciar nesse diretório. `santafé -P` desativa
esse carregador (útil em ferramentas de análise). Não exporte caminhos globais
para misturar instalações de projetos diferentes.

`--permitir-nativo` deve ser repetido em instalações que contenham código C.
O compilador usa receitas declarativas; isso não torna seguro código hostil.
Não há hooks arbitrários de shell nem scripts de pós-instalação. O código Fé
também pode acessar recursos do usuário quando o programa o importa.

## Formatos e limites implementados

Identificadores de pacotes: ASCII minúsculo, números e hífen; 1–64 caracteres,
sem hífen inicial/final. Nomes de módulos Santafé continuam Unicode.
SemVer de três componentes, com pré-lançamentos; componentes até 2.147.483.647.
Intervalos: exato, `^`, `~`, comparadores combinados e `||`, além de curingas
numéricos. Intervalos malformados são erro, nunca “qualquer versão”.

Máximo inicial: 128 dependências resolvidas, 256 versões por pacote, 20.000
passos de resolução. Limites excedidos são falha explícita, não resolução parcial.
O arquivo de pacote é um envelope de dados versionado com conteúdo Base64 e
SHA-256 por arquivo; não é um tar com permissões/links executáveis embutidos.
A extensão é `.sfp`, JSON UTF-8: `formato`, `manifesto`, `arquivos`. Cada arquivo
tem `caminho`, `sha256` e `base64`. Manifestos de biblioteca exigem `nome`,
`versao`, `descricao`, `licenca`, `autores`, `fonte` HTTPS e lista `arquivos`;
opcionalmente `dependencias`, `modulos` e `nativos`. Campos desconhecidos são
recusados. Todo pacote contém `README.md` e `LICENSE`. `modulos` mapeia nomes
Santafé para fontes `.fé`/`.fe`; `nativos` mapeia nomes C para `fontes` e
`bibliotecas` (nomes de link, sem flags de shell). Não há download de binários
pré-compilados na primeira versão.

O índice `indice.json` usa `formato: 1` e
`pacotes[nome][versao] = {arquivo, sha256, dependencias}`. O caminho canônico é
`pacotes/nome/versao/sha256.sfp`. O catálogo inicial é curado no arquivo
`bibliotecas/catalogo.json`; o primeiro pacote real é `semver 1.0.0`, derivado
do resolvedor testado, não um pacote ilustrativo vazio.

Limites de entrada: índice 4 MiB, 10.000 pacotes; envelope 48 MiB, 512 arquivos,
8 MiB por arquivo e 32 MiB de conteúdo por pacote. Uma instalação aceita até
8.192 arquivos, 128 MiB de conteúdo e 32 módulos nativos. Compilação: 120 s por
módulo, saída limitada; downloads: 60 s, até três redirecionamentos HTTPS.
Limites não são uma promessa de sandbox ou um teto rígido de RSS.

### Transação, recuperação e disco

O estado atômico `.santafe/estado.json` aponta para uma geração privada.
Os manifestos de raiz são espelhos; a biblioteca em execução continua na
geração anterior até a troca de estado. `.santafe/transacao.json` guarda o
journal. Uma nova execução de `instale` recupera a operação interrompida:
antes do commit restaura os espelhos; depois finaliza a geração nova. Edições
manuais concorrentes são preservadas e causam erro explícito, não sobrescrita.

Cache e gerações anteriores são retidos, inclusive preparações interrompidas.
Não há coleta automática nem quota acumulada de disco nesta versão. Para
recriar um projeto, conserve manifesto/lock e faça uma instalação travada num
diretório novo; não apague a geração que algum processo ainda esteja usando.
Um cache adulterado é erro, não motivo para aceitá-lo ou baixar por cima em silêncio.

### Curadoria e montagem (sem publicação)

```sh
santafé empacote /caminho/fonte /caminho/pacote.sfp
santafé catalogo /caminho/catalogo /caminho/pacote.sfp
python3 operação/preparar-catalogo-bibliotecas.py --saida /tmp/catalogo-novo
```

O último comando constrói página, índice, envelopes e `SHA256SUMS` a partir de
fontes explicitamente enumerados. `--anterior DIRETORIO` incorpora todas as
versões anteriores, revalidando os envelopes e recusando substituições.
Não lê `.env`, credenciais, arquivos de trabalho ou links simbólicos. Apenas
gerar esse diretório não torna o catálogo público.

HTTPS autentica a origem; hashes fixados no lock detectam alteração de conteúdo.
Isso não equivale a uma infraestrutura de assinatura independente do servidor.
Não anunciar verificação criptográfica de autoria sem implementá-la e distribuir
uma raiz de confiança. Segredos de publicação nunca entram nos pacotes.

## Gates obrigatórios

1. Testes de SemVer, resolução/backtracking, diamantes, conflitos e ciclos.
2. Instalação limpa e repetida, offline, lock adulterado, pacote corrompido,
   travessia, symlinks, concorrência e interrupções antes/depois da troca.
3. Módulo Fé e módulo C reais, compilação permitida/recusada e isolamento
   entre dois projetos com versões diferentes.
4. macOS e Debian, prefixos com espaços, regressão do núcleo/SLS/editores.
5. Catálogo/publicador reversíveis, documentação e comando de publicação
   conferidos antes de cada publicação.

Ensaios macOS e Debian concluídos: cliente real, prefixo com espaços, TLS,
lock/offline, módulo C, integração SLS, memória/descritores, seis fronteiras
de interrupção e isolamento entre projetos. Catálogo determinístico e biblioteca
real conferidos no macOS e no preflight conjunto Debian. Publicador e distribuição
passaram pelos ensaios isolados. A homologação final, incluindo o host/visual
Sublime e a inspeção visual VS Code, foi concluída em 21/10; consulte
`HOMOLOGACAO-CONJUNTA.json`, registro histórico anterior à publicação.
A publicação posterior e as verificações do catálogo e da instalação estão
registradas em [LANCAMENTO-2.1.0](LANCAMENTO-2.1.0.md).
Não existe ainda repositório público 1.0 pronto para consumo.
