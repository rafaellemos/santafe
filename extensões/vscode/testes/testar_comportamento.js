"use strict";

/* Ensaio sem VS Code instalado: fornece somente a API usada pela extensão e
 * confirma conclusões, ajuda e navegação local. Execute com Node.js. */
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const raiz = path.resolve(__dirname, "..");
const temporário = fs.mkdtempSync(path.join(os.tmpdir(), "santafe-vscode-"));
const registrados = {};

const apiFalsa = `
const registrados = {};
class Position { constructor(line, character) { this.line = line; this.character = character; } }
class Range { constructor(start, end) { this.start = start; this.end = end; } }
class CompletionItem { constructor(label, kind) { this.label = label; this.kind = kind; } }
class SnippetString { constructor(value) { this.value = value; } }
class MarkdownString { constructor(value = "") { this.value = value; } appendCodeblock(value) { this.value += value; } appendMarkdown(value) { this.value += value; } }
class Diagnostic { constructor() {} }
class DocumentSymbol { constructor(name, detail, kind, range, selectionRange) {
  const before = (a, b) => a.line < b.line || (a.line === b.line && a.character <= b.character);
  if (!before(range.start, selectionRange.start) || !before(selectionRange.end, range.end))
    throw new Error('selectionRange must be contained in fullRange');
  this.name = name; this.detail = detail; this.kind = kind; this.range = range; this.selectionRange = selectionRange;
} }
class Location { constructor(uri, range) { this.uri = uri; this.range = range; } }
class Hover { constructor(contents) { this.contents = contents; } }
const descarte = { dispose() {} };
module.exports = {
  EventEmitter: class {fire(){} dispose(){} event(){return descarte;}},
  CodeActionKind: {QuickFix:"quickfix"},
  Position, Range, CompletionItem, SnippetString, MarkdownString, Diagnostic, DocumentSymbol, Location, Hover,
  CompletionItemKind: { Keyword: 1, Module: 2, Variable: 3, Method: 4, Function: 5 },
  SemanticTokensLegend: class { constructor(types, modifiers) { this.tokenTypes = types; this.tokenModifiers = modifiers; } },
  SymbolKind: { Function: 12 }, DiagnosticSeverity: { Error: 1, Warning: 2, Information: 3, Hint: 4 },
  window: { createOutputChannel() { return { appendLine() {}, append() {}, show() {}, dispose() {} }; }, showWarningMessage() {} },
  languages: {
    registerReferenceProvider(){return descarte;}, registerDocumentHighlightProvider(){return descarte;},
    registerRenameProvider(){return descarte;}, registerSignatureHelpProvider(){return descarte;},
    registerDocumentFormattingEditProvider(){return descarte;}, registerFoldingRangeProvider(){return descarte;},
    registerSelectionRangeProvider(){return descarte;}, registerCodeActionsProvider(){return descarte;},
    registerWorkspaceSymbolProvider(){return descarte;},
    registerDocumentSemanticTokensProvider(_, provider) { registrados.realce = provider; return descarte; },
    createDiagnosticCollection() { return { delete() {}, set() {}, dispose() {} }; },
    registerCompletionItemProvider(_, provider) { registrados.conclusões = provider; return descarte; },
    registerHoverProvider(_, provider) { registrados.ajuda = provider; return descarte; },
    registerDocumentSymbolProvider(_, provider) { registrados.símbolos = provider; return descarte; },
    registerDefinitionProvider(_, provider) { registrados.definições = provider; return descarte; }
  },
  workspace: {
    createFileSystemWatcher(){return {dispose(){},onDidCreate(){return descarte;},onDidChange(){return descarte;},onDidDelete(){return descarte;}};},
    onDidChangeWorkspaceFolders(){return descarte;},
    textDocuments: [], workspaceFolders: undefined,
    getConfiguration() { return { get(chave, padrão) { return chave === "enable" ? false : padrão; }, inspect() { return {}; } }; },
    onDidOpenTextDocument() { return descarte; }, onDidChangeTextDocument() { return descarte; },
    onDidSaveTextDocument() { return descarte; }, onDidCloseTextDocument() { return descarte; }, onDidChangeConfiguration() { return descarte; }
  },
  commands: { registerCommand() { return descarte; } }, Uri: { parse(valor) { return { toString: () => valor }; } },
  __registrados: registrados
};
`;

function documento(texto) {
  const linhas = texto.split("\n");
  const inícioDaLinha = (linha) => linhas.slice(0, linha).reduce((total, atual) => total + atual.length + 1, 0);
  return {
    languageId: "santafe", uri: { toString: () => "file:///teste.fé" },
    getText(intervalo) {
      if (!intervalo) return texto;
      if (intervalo.start.line !== intervalo.end.line) return "";
      return linhas[intervalo.start.line].slice(intervalo.start.character, intervalo.end.character);
    },
    lineAt(linha) { return { text: linhas[linha], range: { end: { line: linha, character: linhas[linha].length } } }; },
    getWordRangeAtPosition(posição, padrão = /[\p{L}\p{M}\p{N}_]+/u) {
      const linha = linhas[posição.line];
      for (const match of linha.matchAll(new RegExp(padrão.source, "gu"))) {
        const começo = match.index, fim = começo + match[0].length;
        if (começo <= posição.character && posição.character <= fim)
          return {start: {line: posição.line, character: começo}, end: {line: posição.line, character: fim}};
      }
      return undefined;
    },
    positionAt(offset) {
      let linha = 0;
      while (linha + 1 < linhas.length && inícioDaLinha(linha + 1) <= offset) linha++;
      return { line: linha, character: offset - inícioDaLinha(linha) };
    }
  };
}

try {
  fs.mkdirSync(path.join(temporário, "node_modules", "vscode"), { recursive: true });
  fs.copyFileSync(path.join(raiz, "extension.js"), path.join(temporário, "extension.js"));
  fs.copyFileSync(path.join(raiz, "package.json"), path.join(temporário, "package.json"));
  fs.copyFileSync(path.join(raiz, "api-publica.json"), path.join(temporário, "api-publica.json"));
  for (const nome of ["realce-vscode.js", "realce-embutido.js", "aparencia.js", "paletas.json", "provedores-sls.js"])
    fs.copyFileSync(path.join(raiz, nome), path.join(temporário, nome));
  fs.writeFileSync(path.join(temporário, "node_modules", "vscode", "index.js"), apiFalsa);

  const extensão = require(path.join(temporário, "extension.js"));
  extensão.activate({ subscriptions: [] });
  const vscode = require(path.join(temporário, "node_modules", "vscode"));
  const fonte = documento("local função saudação(nome) início\n    mostre(nome)\nfim\ncorreio.");

  const gerais = vscode.__registrados.conclusões.provideCompletionItems(fonte, { line: 1, character: 10 });
  assert(gerais.some((item) => item.label === "mostre"));
  assert(gerais.some((item) => item.label === "saudação"));
  const membros = vscode.__registrados.conclusões.provideCompletionItems(fonte, { line: 3, character: 8 });
  assert(membros.some((item) => item.label === "novaMensagem"));
  const colar = vscode.__registrados.conclusões.provideCompletionItems(documento("colar."), {line: 0, character: 6});
  assert(colar.some(item => item.label === "tamanho"), 'catálogo deve incluir o núcleo C');
  assert(vscode.__registrados.ajuda.provideHover(fonte, { line: 1, character: 10 }));
  assert.strictEqual(vscode.__registrados.símbolos.provideDocumentSymbols(fonte)[0].name, "saudação");
  for (const quebra of ["\n", "\r\n"]) {
    for (const nome of ["saudação", "saudac\u0327a\u0303o", "loc", "fun"]) {
      const doc = documento(["-- 🟢", "", "", `\tlocal função ${nome}()`, "fim"].join(quebra));
      const símbolo = vscode.__registrados.símbolos.provideDocumentSymbols(doc)[0];
      assert.strictEqual(símbolo.name, nome);
      assert.strictEqual(símbolo.range.start.line, 3);
      assert.strictEqual(símbolo.selectionRange.start.line, 3);
      assert.strictEqual(símbolo.selectionRange.start.character, "\tlocal função ".length);
      assert.strictEqual(doc.getText(símbolo.selectionRange), nome);
    }
  }
  assert(vscode.__registrados.definições.provideDefinition(fonte, { line: 0, character: 16 }));
  for (const nome of ["saudação", "saudac\u0327a\u0303o", "i\u0301ndice"]) {
    const doc = documento(`local função ${nome}()\nfim\n${nome}()`);
    const destino = vscode.__registrados.definições.provideDefinition(doc, {line: 2, character: nome.length - 1});
    assert(destino, `navegação local deve preservar ${nome}`);
    assert.strictEqual(doc.getText(destino.range), nome);
  }
  extensão.deactivate();
  console.log("Extensão VS Code: conclusões, ajuda e símbolos locais: ok");
} finally {
  fs.rmSync(temporário, { recursive: true, force: true });
}
