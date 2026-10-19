"use strict";
// Use Node com vscode-textmate/vscode-oniguruma, ou Electron do VS Code com
// ELECTRON_RUN_AS_NODE=1 e --app /caminho/Contents/Resources/app.
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const appIndex = process.argv.indexOf("--app");
const app = appIndex < 0 ? undefined : process.argv[appIndex + 1];
const modules = app ? path.join(app, "node_modules.asar") : "";
const tm = require(modules ? path.join(modules, "vscode-textmate") : "vscode-textmate");
const onig = require(modules ? path.join(modules, "vscode-oniguruma") : "vscode-oniguruma");
const wasm = modules ? path.join(app, "node_modules.asar.unpacked/vscode-oniguruma/release/onig.wasm") : require.resolve("vscode-oniguruma/release/onig.wasm");
const raiz = path.resolve(__dirname, "../..");
const {realce} = require("../realce-embutido");

(async () => {
  await onig.loadWASM(fs.readFileSync(wasm));
  const registry = new tm.Registry({
    onigLib: Promise.resolve({createOnigScanner: s => new onig.OnigScanner(s), createOnigString: s => new onig.OnigString(s)}),
    loadGrammar: async scope => {
      const nomes = {"source.santafe": path.join(raiz, "vscode/syntaxes/santafe.tmLanguage.json"),
        "text.html.basic": app && path.join(app, "extensions/html/syntaxes/html.tmLanguage.json"),
        "source.js": app && path.join(app, "extensions/javascript/syntaxes/JavaScript.tmLanguage.json"),
        "source.css": app && path.join(app, "extensions/css/syntaxes/css.tmLanguage.json")};
      if (!nomes[scope]) return null;
      return tm.parseRawGrammar(fs.readFileSync(nomes[scope], "utf8"), nomes[scope]);
    }
  });
  const grammar = await registry.loadGrammar("source.santafe");
  const casos = JSON.parse(fs.readFileSync(path.join(raiz, "testes/realce.json"), "utf8"));
  for (const caso of casos) if (caso.arquivo)
    caso.fonte = fs.readFileSync(path.join(raiz, "testes", caso.arquivo), "utf8");
  const falhas = [];
  for (const caso of casos) {
    try {
    let ponto = -1;
    for (let i = 0; i < (caso.ocorrencia || 1); i++) ponto = caso.fonte.indexOf(caso.trecho, ponto + 1);
    assert(ponto >= 0, caso.nome);
    let offset = 0, stack = tm.INITIAL;
    const selecionados = new Array(caso.trecho.length);
    for (const linha of caso.fonte.split("\n")) {
      const resultado = grammar.tokenizeLine(linha, stack);
      stack = resultado.ruleStack;
      // Conferir todos os tokens do trecho, não apenas a primeira letra:
      // o curinga não pode herdar a cor do colar enquanto só o nome é realçado.
      for (const token of resultado.tokens) {
        for (let p = Math.max(ponto, offset + token.startIndex); p < Math.min(ponto + caso.trecho.length, offset + token.endIndex); p++)
          selecionados[p - ponto] = token.scopes.join(" ");
      }
      offset += linha.length + 1;
    }
    // Pipeline real: base Santafé + camada HTML/JS mapeada aos literais.
    for (const token of await realce(caso.fonte, scope => registry.loadGrammar(scope)))
      for (let p = Math.max(ponto, token.início); p < Math.min(ponto + caso.trecho.length, token.fim); p++)
        selecionados[p - ponto] = token.scopes.join(" ");
    assert(selecionados.length, caso.nome);
    for (const escopos of selecionados) {
      if (caso.tem) assert(escopos.includes(caso.tem), `${caso.nome}: ${escopos}`);
      if (caso.tem_um) assert(caso.tem_um.some(s => escopos.includes(s)), `${caso.nome}: ${escopos}`);
      if (caso.nao) assert(!escopos.includes(caso.nao), `${caso.nome}: ${escopos}`);
    }
    } catch (erro) { falhas.push(erro.message); }
  }
  assert.deepStrictEqual(falhas, [], falhas.join("\n"));
  if (app) {
    // Escopo correto não basta: reproduzir o problema visual com temas reais.
    function coresDoTema(arquivo) {
      const tema = JSON.parse(fs.readFileSync(arquivo, "utf8"));
      return [...(tema.include ? coresDoTema(path.resolve(path.dirname(arquivo), tema.include)) : []),
        ...(tema.tokenColors || [])];
    }
    for (const arquivo of ["theme-defaults/themes/dark_plus.json", "theme-monokai/themes/monokai-color-theme.json"]) {
      registry.setTheme({settings: coresDoTema(path.join(app, "extensions", arquivo))});
      const linha = "local a = `Texto ®nome e ®{nome}`";
      const tokens = grammar.tokenizeLine2(linha, tm.INITIAL).tokens;
      function cor(trecho) {
        const posição = linha.indexOf(trecho);
        let metadados;
        for (let i = 0; i < tokens.length && tokens[i] <= posição; i += 2) metadados = tokens[i + 1];
        return registry.getColorMap()[(metadados >>> 15) & 0x1ff];
      }
      assert.strictEqual(cor("®nome"), cor("nome"), `curinga separado da variável: ${arquivo}`);
      assert.notStrictEqual(cor("®nome"), cor("Texto"), `variável com cor do colar: ${arquivo}`);
      assert.notStrictEqual(cor("®{"), cor("Texto"), `curinga da expressão com cor do colar: ${arquivo}`);
      assert.strictEqual(cor("®{"), cor("{"), `marcador separado da chave: ${arquivo}`);
      assert.strictEqual(cor("®{"), cor("}"), `delimitadores inconsistentes: ${arquivo}`);
    }
    console.log("TextMate real: cores do curinga em Dark+ e Monokai: ok");
  }
  registry.dispose();
  console.log(`TextMate + camada embutida: ${casos.length} casos de interpolação, HTML, JS e isolamento: ok`);
})().catch(e => { console.error(e); process.exitCode = 1; });
