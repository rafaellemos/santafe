"use strict";

const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const vscode = require("vscode");

const LINGUAGEM = "santafe";
const VERSÃO_EXTENSÃO = JSON.parse(fs.readFileSync(path.join(__dirname, "package.json"), "utf8")).version;

/* O catálogo é gerado do manifesto da API pública. Ele não substitui uma
 * análise semântica: oferece, desde já, nomes confiáveis e independentes do
 * processo SLS para a primeira experiência no editor. */
function leiaCatálogoPúblico() {
  try {
    const caminho = path.join(__dirname, "api-publica.json");
    const catálogo = JSON.parse(fs.readFileSync(caminho, "utf8"));
    return Array.isArray(catálogo.itens) ? catálogo.itens : [];
  } catch (erro) {
    console.error(`Santafé: não foi possível ler o catálogo público: ${erro.message}`);
    return [];
  }
}

const CATÁLOGO_PÚBLICO = leiaCatálogoPúblico();

const PALAVRAS_RESERVADAS = [
  "local", "função", "retorne", "se", "então", "senão", "enquanto", "para",
  "em", "repita", "até", "início", "fim", "pare", "vápara", "nulo",
  "verdadeiro", "falso", "e", "ou", "não"
];

const FUNÇÕES_DO_NÚCLEO = [
  { rótulo: "mostre", detalhe: "função global", documentação: "Exibe valores na saída padrão.", inserção: "mostre(${1})" },
  { rótulo: "tipo", detalhe: "função global", documentação: "Devolve o tipo lógico de um valor.", inserção: "tipo(${1:valor})" },
  { rótulo: "tamanho", detalhe: "função global", documentação: "Conta grafemas de um colar; em tabelas, segue o operador #.", inserção: "tamanho(${1:valor})" },
  { rótulo: "octetos", detalhe: "função global", documentação: "Mede os octetos de um colar, útil para protocolos e dados binários.", inserção: "octetos(${1:dados})" },
  { rótulo: "importe", detalhe: "função global", documentação: "Carrega uma biblioteca Santafé.", inserção: "importe \"${1:biblioteca}\"" },
  { rótulo: "carregue", detalhe: "função global", documentação: "Compila um colar sem o executar.", inserção: "carregue(${1:fonte})" },
  { rótulo: "carregueArquivo", detalhe: "função global", documentação: "Compila um arquivo sem o executar.", inserção: "carregueArquivo(${1:caminho})" },
  { rótulo: "executeArquivo", detalhe: "função global", documentação: "Executa um arquivo Santafé.", inserção: "executeArquivo(${1:caminho})" },
  { rótulo: "garanta", detalhe: "função global", documentação: "Interrompe a execução quando a condição não é verdadeira.", inserção: "garanta(${1:condição}, ${2:mensagem})" },
  { rótulo: "proteja", detalhe: "função global", documentação: "Executa uma função protegida e devolve sucesso, resultado ou falha.", inserção: "proteja(função()\n    ${0}\nfim)" },
  { rótulo: "protejaMais", detalhe: "função global", documentação: "Executa uma função protegida com tratador de falhas.", inserção: "protejaMais(${1:função}, ${2:tratador})" },
  { rótulo: "paraNúmero", detalhe: "função global", documentação: "Converte um valor em número quando possível.", inserção: "paraNúmero(${1:valor})" },
  { rótulo: "paraColar", detalhe: "função global", documentação: "Converte um valor em colar.", inserção: "paraColar(${1:valor})" },
  { rótulo: "pares", detalhe: "função global", documentação: "Itera as chaves de uma tabela.", inserção: "pares(${1:tabela})" },
  { rótulo: "ipares", detalhe: "função global", documentação: "Itera a sequência numérica inicial de uma tabela.", inserção: "ipares(${1:tabela})" },
  { rótulo: "próximo", detalhe: "função global", documentação: "Avança manualmente sobre as chaves de uma tabela.", inserção: "próximo(${1:tabela})" },
  { rótulo: "erro", detalhe: "função global", documentação: "Interrompe a execução com uma falha.", inserção: "erro(${1:mensagem})" },
  { rótulo: "coleteLixo", detalhe: "função global", documentação: "Controla o coletor de lixo.", inserção: "coleteLixo(${1:opção})" }
];

const BIBLIOTECAS = [
  "arquivo", "bit32", "caminheiro", "colar", "correio", "es", "imagem", "json",
  "mariadb", "mat", "nomes", "pulso", "rede", "rpdf", "segredo", "tomada", "turing", "vigia",
  "tabela", "corrotina", "depure", "módulo", "so", "utf8"
];

const INFORMAÇÕES = new Map();
for (const função of FUNÇÕES_DO_NÚCLEO) INFORMAÇÕES.set(função.rótulo, função);
for (const item of CATÁLOGO_PÚBLICO) {
  if (!INFORMAÇÕES.has(item.rótulo)) {
    INFORMAÇÕES.set(item.rótulo, {
      rótulo: item.rótulo,
      detalhe: item.categoria,
      documentação: `API pública em \`${item.origem}\`.`
    });
  }
}

function tipoDaConclusão(rótulo) {
  if (rótulo.includes(":")) return vscode.CompletionItemKind.Method;
  if (rótulo.includes(".")) return vscode.CompletionItemKind.Function;
  return vscode.CompletionItemKind.Function;
}

function contextoDeAcesso(documento, posição) {
  const antes = documento.lineAt(posição.line).text.slice(0, posição.character);
  const encontrado = /((?:[\p{L}_][\p{L}\p{M}\p{N}_]*[.:])+)([\p{L}\p{M}\p{N}_]*)$/u.exec(antes);
  return encontrado ? encontrado[1] : "";
}

function nomesLocais(documento) {
  const nomes = new Set();
  const fonte = documento.getText();
  const funções = /^[\t ]*(?:local[\t ]+)?função[\t ]+([\p{L}_][\p{L}\p{M}\p{N}_]*)/gmu;
  const locais = /\blocal\s+([\p{L}_][\p{L}\p{M}\p{N}_]*)/gu;
  for (const padrão of [funções, locais]) {
    let encontrado;
    while ((encontrado = padrão.exec(fonte)) !== null) nomes.add(encontrado[1]);
  }
  return [...nomes].sort((a, b) => a.localeCompare(b, "pt-BR"));
}

function conclusão(rótulo, detalhe, tipo, inserção, documentação) {
  const item = new vscode.CompletionItem(rótulo, tipo);
  item.detail = detalhe;
  item.documentation = new vscode.MarkdownString(documentação || detalhe);
  if (inserção) item.insertText = new vscode.SnippetString(inserção);
  return item;
}

function conclusõesDoSantafé(documento, posição) {
  const acesso = contextoDeAcesso(documento, posição);
  const itens = [];

  if (!acesso) {
    for (const palavra of PALAVRAS_RESERVADAS) {
      itens.push(conclusão(palavra, "palavra reservada", vscode.CompletionItemKind.Keyword));
    }
    for (const biblioteca of BIBLIOTECAS) {
      itens.push(conclusão(biblioteca, "biblioteca Santafé", vscode.CompletionItemKind.Module));
    }
    for (const nome of nomesLocais(documento)) {
      itens.push(conclusão(nome, "símbolo deste arquivo", vscode.CompletionItemKind.Variable));
    }
  }

  for (const informação of INFORMAÇÕES.values()) {
    if (acesso && !informação.rótulo.startsWith(acesso)) continue;
    const rótulo = acesso ? informação.rótulo.slice(acesso.length) : informação.rótulo;
    itens.push(conclusão(
      rótulo,
      acesso ? `${informação.rótulo} — ${informação.detalhe}` : informação.detalhe,
      tipoDaConclusão(informação.rótulo),
      acesso ? undefined : informação.inserção,
      informação.documentação
    ));
  }
  return itens;
}

function informaçãoDoSímbolo(documento, posição) {
  const intervalo = documento.getWordRangeAtPosition(posição, /[\p{L}\p{M}\p{N}_]+/u);
  if (!intervalo) return undefined;
  const palavra = documento.getText(intervalo);
  const acesso = contextoDeAcesso(documento, posição);
  return INFORMAÇÕES.get(acesso + palavra) || INFORMAÇÕES.get(palavra);
}

function símboloDaFunção(documento, nome) {
  const padrão = /^[\t ]*(?:local[\t ]+)?função[\t ]+([\p{L}_][\p{L}\p{M}\p{N}_]*)/gmu;
  let encontrado;
  while ((encontrado = padrão.exec(documento.getText())) !== null) {
    if (encontrado[1] !== nome) continue;
    const início = documento.positionAt(encontrado.index + encontrado[0].length - nome.length);
    const fim = new vscode.Position(início.line, início.character + nome.length);
    return new vscode.Location(documento.uri, new vscode.Range(início, fim));
  }
  return undefined;
}

function símbolosDoDocumento(documento) {
  const símbolos = [];
  const padrão = /^[\t ]*(?:local[\t ]+)?função[\t ]+([\p{L}_][\p{L}\p{M}\p{N}_]*)/gmu;
  const fonte = documento.getText();
  let encontrado;
  while ((encontrado = padrão.exec(fonte)) !== null) {
    const início = documento.positionAt(encontrado.index);
    const nome = encontrado[1];
    const posiçãoDoNome = documento.positionAt(encontrado.index + encontrado[0].length - nome.length);
    const alcance = new vscode.Range(início, documento.lineAt(início.line).range.end);
    const seleção = new vscode.Range(posiçãoDoNome, new vscode.Position(posiçãoDoNome.line, posiçãoDoNome.character + nome.length));
    símbolos.push(new vscode.DocumentSymbol(nome, "função Santafé", vscode.SymbolKind.Function, alcance, seleção));
  }
  return símbolos;
}

/** Adaptador stdio limitado, com negociação, cancelamento e fallback local. */
class ClienteSls {
  constructor(contexto) {
    this.contexto = contexto;
    this.saída = vscode.window.createOutputChannel("Santafé SLS");
    this.diagnósticos = vscode.languages.createDiagnosticCollection("Santafé");
    this.processo = undefined;
    this.pronto = false;
    this.encerrando = false;
    this.próximoId = 1;
    this.buffer = Buffer.alloc(0);
    this.documentos = new Map();
    this.versõesEnviadas = new Map();
    this.reinício = undefined;
    this.capacidades = {};
    this.pendentes = new Map();
    this.aoMudarEstado = new vscode.EventEmitter();
  }

  configuração() {
    return vscode.workspace.getConfiguration("santafe.languageServer");
  }

  configuraçãoFoiDefinida(chave) {
    const inspeção = this.configuração().inspect(chave);
    if (!inspeção) return false;
    return [
      "globalValue",
      "workspaceValue",
      "workspaceFolderValue",
      "globalLanguageValue",
      "workspaceLanguageValue",
      "workspaceFolderLanguageValue"
    ].some((campo) => inspeção[campo] !== undefined);
  }

  execuçãoDoSls() {
    const configuração = this.configuração();
    const configuraçãoExplícita = this.configuraçãoFoiDefinida("command") ||
      this.configuraçãoFoiDefinida("args");

    /* Ao editar o próprio Santafé, não é preciso instalar o núcleo: o binário
     * recém-compilado e o fonte do SLS formam um par autocontido. */
    const pasta = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    const executável = process.platform === "win32" ? "santafe.exe" : "santafé";
    const binárioDoFonte = pasta && path.join(pasta, "src", executável);
    const fonteDoSls = pasta && path.join(pasta, "ferramentas", "sls", "sls.fé");
    if (!configuraçãoExplícita && binárioDoFonte && fonteDoSls &&
        fs.existsSync(binárioDoFonte) && fs.existsSync(fonteDoSls)) {
      return {
        comando: binárioDoFonte,
        // O servidor não deve ativar o carregador de bibliotecas do projeto.
        argumentos: ["-E", "-P", fonteDoSls],
        origem: "fonte do projeto"
      };
    }

    const comando = !configuraçãoExplícita && process.platform === "win32"
      ? "santafe-sls.exe" : configuração.get("command", "santafé-sls");
    const argumentosConfigurados = configuração.get("args", []);
    if (!configuraçãoExplícita && process.platform !== "win32") {
      const caminhos = ["/usr/local/bin/santafé-sls", path.join(require("os").homedir(), ".local/bin/santafé-sls")];
      for (const caminho of caminhos) {
        try {
          fs.accessSync(caminho, fs.constants.X_OK);
          return {comando: caminho, argumentos: [], origem: "instalação local detectada"};
        } catch (_) { /* tentar próximo local */ }
      }
    }
    return {
      comando,
      argumentos: Array.isArray(argumentosConfigurados) ? argumentosConfigurados : [],
      origem: "instalação configurada"
    };
  }

  registre(documento) {
    if (![LINGUAGEM,"onfe"].includes(documento.languageId)) return;
    this.documentos.set(documento.uri.toString(), documento);
    if (this.pronto) this.envieAbertura(documento);
  }

  atualize(documento, mudanças) {
    if (![LINGUAGEM,"onfe"].includes(documento.languageId)) return;
    this.documentos.set(documento.uri.toString(), documento);
    if (!this.pronto) return;
    if (documento.version <= (this.versõesEnviadas.get(documento.uri.toString()) || 0)) return;
    this.versõesEnviadas.set(documento.uri.toString(),documento.version);
    this.notifique("textDocument/didChange", {
      textDocument: { uri: documento.uri.toString(), version: documento.version },
      // Os intervalos de um evento VS Code referem-se ao documento anterior.
      // Ordem decrescente os torna alterações sequenciais válidas em LSP.
      contentChanges: this.capacidades.textDocumentSync?.change === 2 && mudanças?.length
        ? [...mudanças].sort((a,b)=>b.rangeOffset-a.rangeOffset).map(m=>({
          range:{start:{line:m.range.start.line,character:m.range.start.character},
                 end:{line:m.range.end.line,character:m.range.end.character}},
          rangeLength:m.rangeLength, text:m.text}))
        : [{ text: documento.getText() }]
    });
  }

  salve(documento) {
    if (![LINGUAGEM,"onfe"].includes(documento.languageId) || !this.pronto) return;
    this.notifique("textDocument/didSave", {
      textDocument: { uri: documento.uri.toString() },
      text: documento.getText()
    });
  }

  feche(documento) {
    if (![LINGUAGEM,"onfe"].includes(documento.languageId)) return;
    const uri = documento.uri.toString();
    this.documentos.delete(uri);
    this.versõesEnviadas.delete(uri);
    this.diagnósticos.delete(documento.uri);
    if (this.pronto) {
      this.notifique("textDocument/didClose", { textDocument: { uri } });
    }
  }

  inicie() {
    if (vscode.workspace.isTrusted === false) return;
    if (this.processo || !this.configuração().get("enable", true)) return;

    const execução = this.execuçãoDoSls();
    const { comando, argumentos } = execução;
    if (typeof comando !== "string" || comando.trim() === "") {
      this.saída.appendLine("SLS desativado: santafe.languageServer.command está vazio.");
      return;
    }

    this.encerrando = false;
    this.pronto = false;
    this.buffer = Buffer.alloc(0);
    this.saída.appendLine(
      `Iniciando SLS (${execução.origem}): ${comando} ${argumentos.join(" ")}`
    );
    const processo = spawn(comando, argumentos, {
      cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
      stdio: ["pipe", "pipe", "pipe"],
      env: process.env
    });
    this.processo = processo;
    processo.stdout.on("data", (trecho) => {
      if (this.processo === processo) this.leiaSaída(trecho);
    });
    processo.stdin.on("error", (erro) => {
      if (this.processo === processo) this.aviseFalha(erro);
    });
    processo.stderr.on("data", (trecho) => {
      this.saída.append(Buffer.from(trecho).toString("utf8"));
    });
    processo.on("error", (erro) => {
      if (this.processo !== processo) return;
      this.processo = undefined;
      this.pronto = false;
      this.cancelePendentes();
      this.aviseFalha(erro);
    });
    processo.on("close", (código, sinal) => {
      if (this.processo !== processo) return;
      this.processo = undefined;
      this.pronto = false;
      this.cancelePendentes();
      if (!this.encerrando) {
        this.saída.appendLine(`SLS encerrou (código ${código ?? "nulo"}, sinal ${sinal ?? "nenhum"}).`);
      }
    });

    this.idInicialização = this.próximoId++;
    this.escreva({
      jsonrpc: "2.0",
      id: this.idInicialização,
      method: "initialize",
      params: {
        processId: process.pid,
        rootUri: vscode.workspace.workspaceFolders?.[0]?.uri.toString() ?? null,
        workspaceFolders: (vscode.workspace.workspaceFolders || []).map(f=>({uri:f.uri.toString(),name:f.name})),
        capabilities: {
          general:{positionEncodings:["utf-16"]},
          workspace:{workspaceFolders:true,workspaceEdit:{documentChanges:true}},
          textDocument: { publishDiagnostics: { relatedInformation: false,versionSupport:true },
            completion:{completionItem:{snippetSupport:false}},rename:{prepareSupport:true},
            semanticTokens:{requests:{full:true},formats:["relative"],
              tokenTypes:["variable","function","parameter"],tokenModifiers:["declaration"]} }
        },
        initializationOptions: {avisosEscopo:this.configuração().get("scopeWarnings",false)},
        clientInfo: { name: "Santafé para VS Code", version: VERSÃO_EXTENSÃO }
      }
    });
  }

  reinicie() {
    this.pare();
    clearTimeout(this.reinício);
    this.reinício = setTimeout(() => this.inicie(), 100);
  }

  pare() {
    clearTimeout(this.reinício);
    const processo = this.processo;
    this.processo = undefined;
    this.pronto = false;
    this.encerrando = true;
    this.cancelePendentes();
    if (!processo || processo.killed) return;
    try {
      this.escrevaNoProcesso(processo, {
        jsonrpc: "2.0", id: this.próximoId++, method: "shutdown", params: {}
      });
      this.escrevaNoProcesso(processo, { jsonrpc: "2.0", method: "exit", params: {} });
      processo.stdin.end();
      setTimeout(() => {
        if (!processo.killed) processo.kill();
      }, 750).unref();
    } catch (_) {
      processo.kill();
    }
  }

  envieAbertura(documento) {
    this.versõesEnviadas.set(documento.uri.toString(),documento.version);
    this.notifique("textDocument/didOpen", {
      textDocument: {
        uri: documento.uri.toString(),
        languageId: documento.languageId,
        version: documento.version,
        text: documento.getText()
      }
    });
  }

  notifique(método, parâmetros) {
    this.escreva({ jsonrpc: "2.0", method: método, params: parâmetros });
  }

  suporta(capacidade) { return this.pronto && !!this.capacidades[capacidade]; }

  cancelePendentes() {
    this.capacidades = {};
    for (const pedido of this.pendentes.values()) pedido.conclua(undefined);
    this.pendentes.clear();
    this.aoMudarEstado.fire();
  }

  solicite(método, parâmetros, cancelamento) {
    if (!this.pronto || cancelamento?.isCancellationRequested) return Promise.resolve(undefined);
    if (this.pendentes.size >= 128) return Promise.reject(new Error("Fila do SLS cheia; tente novamente."));
    const id = this.próximoId++;
    return new Promise((resolve,reject)=>{
      let tempo, inscrição;
      const conclua=(resultado,erro)=>{
        clearTimeout(tempo); inscrição?.dispose(); this.pendentes.delete(id);
        erro ? reject(erro) : resolve(resultado);
      };
      const cancele=()=>{this.notifique("$/cancelRequest",{id}); conclua(undefined);};
      this.pendentes.set(id,{conclua});
      tempo=setTimeout(cancele,10000);
      inscrição=cancelamento?.onCancellationRequested(cancele);
      this.escreva({jsonrpc:"2.0",id,method:método,params:parâmetros});
      if (cancelamento?.isCancellationRequested) cancele();
    });
  }

  escreva(mensagem) {
    if (this.processo) this.escrevaNoProcesso(this.processo, mensagem);
  }

  escrevaNoProcesso(processo, mensagem) {
    const conteúdo = JSON.stringify(mensagem);
    const quadro = `Content-Length: ${Buffer.byteLength(conteúdo, "utf8")}\r\n\r\n${conteúdo}`;
    if (this.configuração().get("trace", false)) {
      this.saída.appendLine(`→ ${conteúdo}`);
    }
    processo.stdin.write(quadro, "utf8");
  }

  leiaSaída(trecho) {
    this.buffer = Buffer.concat([this.buffer, Buffer.from(trecho)]);
    if (this.buffer.length>32*1024*1024) { this.saída.appendLine("SLS: resposta excessiva."); this.pare(); return; }
    while (true) {
      const fimDoCabeçalho = this.buffer.indexOf("\r\n\r\n");
      if (fimDoCabeçalho < 0) {
        if (this.buffer.length>8192) this.pare();
        return;
      }
      const cabeçalho = this.buffer.subarray(0, fimDoCabeçalho).toString("ascii");
      const encontrado = /^content-length:\s*(\d+)\s*$/im.exec(cabeçalho);
      if (!encontrado) {
        this.saída.appendLine("SLS enviou um quadro sem Content-Length; saída descartada.");
        this.buffer = Buffer.alloc(0);
        return;
      }
      const tamanho = Number(encontrado[1]);
      if (fimDoCabeçalho>8192 || !Number.isSafeInteger(tamanho) || tamanho>16*1024*1024 || tamanho<1 ||
          (cabeçalho.match(/^content-length:/gim)||[]).length!==1) {this.pare();return;}
      const início = fimDoCabeçalho + 4;
      if (this.buffer.length < início + tamanho) return;
      const conteúdo = this.buffer.subarray(início, início + tamanho).toString("utf8");
      this.buffer = this.buffer.subarray(início + tamanho);
      try {
        const mensagem = JSON.parse(conteúdo);
        if (this.configuração().get("trace", false)) this.saída.appendLine(`← ${conteúdo}`);
        this.processe(mensagem);
      } catch (erro) {
        this.saída.appendLine(`SLS enviou JSON inválido: ${erro.message}`);
      }
    }
  }

  processe(mensagem) {
    if (!mensagem || mensagem.jsonrpc!=="2.0") return;
    if (mensagem.id===this.idInicialização && mensagem.error) {
      this.saída.appendLine(`SLS recusou inicialização: ${mensagem.error.message}`);
      this.pare(); return;
    }
    if (mensagem.id === this.idInicialização && Object.prototype.hasOwnProperty.call(mensagem, "result")) {
      this.capacidades=mensagem.result?.capabilities || {};
      this.informação=mensagem.result?.serverInfo;
      this.pronto = true;
      this.saída.appendLine(`SLS pronto: ${this.informação?.version || "versão não informada"}`);
      this.notifique("initialized", {});
      for (const documento of this.documentos.values()) this.envieAbertura(documento);
      this.aoMudarEstado.fire();
      return;
    }
    const pendente=this.pendentes.get(mensagem.id);
    if (pendente) {
      const erro=mensagem.error;
      pendente.conclua(mensagem.result,erro && erro.code!==-32800 ? new Error(erro.message) : undefined);
      return;
    }
    if (mensagem.method === "textDocument/publishDiagnostics") {
      this.publiqueDiagnósticos(mensagem.params);
    }
    if(mensagem.method === "window/logMessage") this.saída.appendLine(String(mensagem.params?.message||""));
  }

  publiqueDiagnósticos(parâmetros) {
    if (!parâmetros || typeof parâmetros.uri !== "string") return;
    const documento = this.documentos.get(parâmetros.uri);
    if (documento && typeof parâmetros.version === "number" && parâmetros.version < documento.version) return;
    const uri = vscode.Uri.parse(parâmetros.uri);
    const itens = Array.isArray(parâmetros.diagnostics) ? parâmetros.diagnostics : [];
    const diagnósticos = itens.map((item) => {
      const início = item.range?.start ?? { line: 0, character: 0 };
      const fim = item.range?.end ?? início;
      const alcance = new vscode.Range(
        new vscode.Position(Math.max(0, início.line ?? 0), Math.max(0, início.character ?? 0)),
        new vscode.Position(Math.max(0, fim.line ?? 0), Math.max(0, fim.character ?? 0))
      );
      const diagnóstico = new vscode.Diagnostic(
        alcance,
        String(item.message ?? "Erro de sintaxe"),
        this.severidade(item.severity)
      );
      diagnóstico.source = item.source ?? "SLS";
      diagnóstico.code = item.code;
      return diagnóstico;
    });
    this.diagnósticos.set(uri, diagnósticos);
  }

  severidade(valor) {
    if (valor === 2) return vscode.DiagnosticSeverity.Warning;
    if (valor === 3) return vscode.DiagnosticSeverity.Information;
    if (valor === 4) return vscode.DiagnosticSeverity.Hint;
    return vscode.DiagnosticSeverity.Error;
  }

  aviseFalha(erro) {
    const comando = this.execuçãoDoSls().comando;
    const detalhe = erro && erro.code === "ENOENT"
      ? `O comando “${comando}” não foi encontrado no ambiente deste VS Code.`
      : `Não foi possível iniciar o SLS: ${erro.message}`;
    this.saída.appendLine(detalhe);
    vscode.window.showWarningMessage(`${detalhe} Configure santafe.languageServer.command para corrigir.`);
  }

  descarte() {
    this.pare();
    this.diagnósticos.dispose();
    this.saída.dispose();
    this.aoMudarEstado.dispose();
  }
}

let cliente;

function activate(contexto) {
  cliente = new ClienteSls(contexto);
  const provedores=require("./provedores-sls");
  require("./realce-vscode").registre(vscode, contexto, cliente);
  provedores.registre(vscode,contexto,cliente);
  for (const documento of vscode.workspace.textDocuments) cliente.registre(documento);
  cliente.inicie();

  contexto.subscriptions.push(
    cliente.diagnósticos,
    cliente.saída,
    vscode.workspace.onDidOpenTextDocument((documento) => cliente.registre(documento)),
    vscode.workspace.onDidChangeTextDocument((evento) => cliente.atualize(evento.document,evento.contentChanges)),
    vscode.workspace.onDidSaveTextDocument((documento) => cliente.salve(documento)),
    vscode.workspace.onDidCloseTextDocument((documento) => cliente.feche(documento)),
    vscode.workspace.onDidChangeConfiguration((evento) => {
      if (evento.affectsConfiguration("santafe.languageServer")) cliente.reinicie();
    }),
    vscode.languages.registerCompletionItemProvider(
      { language: LINGUAGEM },
      { provideCompletionItems: (documento, posição, cancelamento) => cliente.suporta("completionProvider")
        ? provedores.complete(vscode,cliente,documento,posição,cancelamento) : conclusõesDoSantafé(documento, posição) },
      ".", ":"
    ),
    vscode.languages.registerHoverProvider(
      { language: LINGUAGEM },
      {
        provideHover(documento, posição, cancelamento) {
          if (cliente.suporta("hoverProvider")) return provedores.hover(vscode,cliente,documento,posição,cancelamento);
          const informação = informaçãoDoSímbolo(documento, posição);
          if (!informação) return undefined;
          const conteúdo = new vscode.MarkdownString();
          conteúdo.appendCodeblock(informação.rótulo, "santafe");
          conteúdo.appendMarkdown(`\n\n${informação.detalhe}. ${informação.documentação || ""}`);
          return new vscode.Hover(conteúdo);
        }
      }
    ),
    vscode.languages.registerDocumentSymbolProvider(
      { language: LINGUAGEM },
      { provideDocumentSymbols: (documento,cancelamento) => cliente.suporta("documentSymbolProvider")
        ? provedores.símbolos(vscode,cliente,documento,cancelamento) : símbolosDoDocumento(documento) }
    ),
    vscode.languages.registerDefinitionProvider(
      { language: LINGUAGEM },
      {
        provideDefinition(documento, posição, cancelamento) {
          if (cliente.suporta("definitionProvider")) return provedores.definição(vscode,cliente,documento,posição,cancelamento);
          const intervalo = documento.getWordRangeAtPosition(posição, /[\p{L}\p{M}\p{N}_]+/u);
          return intervalo ? símboloDaFunção(documento, documento.getText(intervalo)) : undefined;
        }
      }
    ),
    vscode.commands.registerCommand("santafe.reiniciarSLS", () => cliente.reinicie()),
    vscode.commands.registerCommand("santafe.paletaEmbutida", async () => {
      const opção = await vscode.window.showQuickPick([
        {label: "Acompanhar o tema", valor: "tema"},
        {label: "Paleta suave para HTML e JavaScript", valor: "suave"}
      ], {placeHolder: "Cores dos colares HTML/JS, sem alterar outros arquivos"});
      if (opção) await vscode.workspace.getConfiguration("santafe").update(
        "highlight.embeddedPalette", opção.valor, vscode.ConfigurationTarget.Global);
    }),
    vscode.commands.registerCommand("santafe.abrirRegistroSLS", () => cliente.saída.show(true))
  );
  return {estadoSLS:()=>({pronto:cliente.pronto,informação:cliente.informação,capacidades:cliente.capacidades})};
}

function deactivate() {
  cliente?.descarte();
  cliente = undefined;
}

module.exports = { activate, deactivate, ClienteSls, estadoSLS:()=>({pronto:cliente?.pronto,informação:cliente?.informação,capacidades:cliente?.capacidades}) };
