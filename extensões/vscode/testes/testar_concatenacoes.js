"use strict";
// Runtime efetivamente distribuído no VSIX e gramáticas nativas do editor.
const assert = require("assert");
const fs = require("fs"), path = require("path");
const {realce, recorte, documentosEmbutidos} = require("../realce-embutido");
const {crieRegistro, registre, TIPOS, ESCOPOS, tipoDosEscopos} = require("../realce-vscode");
const app = process.argv[process.argv.indexOf("--app") + 1];
assert(app && fs.existsSync(path.join(app, "extensions")), "informe --app /caminho/VSCode/Resources/app");
const extensions = {getExtension(id) {
  const extensionPath = path.join(app, "extensions", id.split(".")[1]);
  return {extensionPath, packageJSON: JSON.parse(fs.readFileSync(path.join(extensionPath, "package.json")))};
}};

(async () => {
  const registro = await crieRegistro(extensions);
  const grammar = s => registro.loadGrammar(s);
  let total = 0;
  async function confira(fonte, trecho, escopo, ocorrência = 1) {
    const tokens = await realce(fonte, grammar);
    let início = -1;
    for (let n = 0; n < ocorrência; n++) início = fonte.indexOf(trecho, início + 1);
    assert(início >= 0, trecho);
    for (let p = início; p < início + trecho.length; p++) {
      const encontrados = tokens.filter(t => t.início <= p && p < t.fim);
      if (escopo) assert(encontrados.some(t => t.scopes.some(s => s.includes(escopo))), `${trecho}: ${JSON.stringify(encontrados)}`);
      else assert.equal(encontrados.length, 0, `código Santafé capturado: ${trecho}`);
    }
    // Qualquer token colorido deve estar inteiramente no conteúdo de um literal.
    const partes = recorte(fonte).literais.flatMap(l => l.partes.filter(p => !p.buraco));
    for (const t of tokens) assert(partes.some(p => t.início >= p.início && t.fim <= p.fim));
    total++;
    return tokens;
  }
  const html = 'local a = [=[<b class="cl-]=] .. web.escapeHTML(nome) .. [=[resto">Olá</b>]=]; mostre(a)';
  await confira(html, "cl-", "string.quoted.double.html");
  await confira(html, "resto", "string.quoted.double.html");
  await confira(html, "web.escapeHTML(nome)", null);
  await confira(html, "mostre", null);
  await confira(html, "]=] ..", null);
  const js = 'local a = --[[javascript]] [=[/* começo ]=] .. nome .. [=[ continuação */ const n=1;]=]; mostre(a)';
  await confira(js, "começo", "comment.block.js");
  await confira(js, "continuação", "comment.block.js");
  await confira(js, "const", "storage.type.js");
  await confira(js, "nome", null);
  await confira(js, "mostre", null);
  const linha = 'local a = --[[javascript]] [=[// antes ]=] .. valor .. [=[depois\nconst fim=1;]=]';
  await confira(linha, "depois", "comment.line");
  await confira(linha, "const", "storage.type");
  for (const n of [1, 3, 100]) {
    const e = "=".repeat(n);
    const s = `local a = [${e}[<b title="x]] ]${e}=] ]${e}] .. chamada('ignorado') .. [${e}[ fim">é🟢</b>]${e}]; mostre(a)`;
    await confira(s, "fim", "string.quoted.double.html");
    await confira(s, "chamada('ignorado')", null);
    await confira(s, "mostre", null);
  }
  await confira('local a = --[[html]] "<b title=\\\"" .. nome .. "fim\\\">Olá</b>"', "fim", "string.quoted.double.html");
  await confira("local a = --[[html]] '<b title=\"' .. nome .. 'fim\">Olá</b>'", "fim", "string.quoted.double.html");
  await confira('local a = [=[<script>/* parte ]=] .. nome .. [=[ final */ const n=1;</script>]=]', "final", "comment.block.js");
  await confira('local a = [=[<script>/* parte ]=] .. nome .. [=[ final */ const n=1;</script>]=]', "const", "storage.type.js");
  await confira('local a = [=[<!-- parte ]=] .. nome .. [=[ final --><h1>Oi</h1>]=]', "final", "comment.block.html");
  await confira('local a = ([=[<b title="]=] .. (nome ou padrão)) .. [=[fim">Oi</b>]=]', "fim", "string.quoted.double.html");
  await confira('local a = [=[<b title="]=] .. web.escapeHTML(nome):troque("x", "y") .. [=[fim">Oi</b>]=]', "fim", "string.quoted.double.html");
  await confira('local a = [=[<b title="]=] .. valores[índice + 1] .. [=[fim">Oi</b>]=]', "fim", "string.quoted.double.html");
  await confira('local a = [=[<b title="]=] .. -- comentário\n nome .. [=[fim">Oi</b>]=]', "fim", "string.quoted.double.html");
  for (const marca of ["®", "Ⓡ"]) {
    const s = `local a = \`<b title="${marca}nome ${marca}{obj({nome='}'})} fim">Oi</b>\``;
    await confira(s, marca + "nome", null);
    await confira(s, marca + "{obj({nome='}'})}", null);
    await confira(s, "fim", "string.quoted.double.html");
  }
  await confira('local a = [=[<b title="incompleto]=]; mostre("não é atributo")', "não é atributo", null);
  await confira('-- local falso = [=[<b title="x">]=]\nlocal real = "comum"', "title", null);
  await confira('local a = --[[html]] [=[<b title="x]=] .. nome .. [=[fim">]=]\nlocal z = "comum"', "comum", null);
  await confira('local a = --[[html]] [=[<b title="x]=] .. (n + 1) .. [=[fim">]=]', "fim", "string.quoted.double.html");
  assert.deepEqual(await realce(html, grammar, () => true), []);
  assert.deepEqual(await realce("x".repeat(1000001), grammar), []);
  assert.deepEqual(await realce('local a = [=[<b>' + 'x'.repeat(20001) + '</b>]=]', grammar), []);
  // Milhares de fragmentos não podem provocar recursão linear ou explosão quadrática.
  const grande = 'local a = [=[<b title="]=] ' + '.. nome .. [=[x]=] '.repeat(3000) + '.. [=[fim">Oi</b>]=]';
  const começo = performance.now();
  const docs = documentosEmbutidos(grande);
  assert.equal(docs.length, 1);
  assert(docs[0].texto.endsWith('fim">Oi</b>'));
  assert(performance.now() - começo < 5000, "recorte muito lento");

  // API real de tokens: validar UTF-16, CRLF, ausência de sobreposição,
  // cancelamento, mudança de versão e correspondência do manifesto.
  const manifesto = require("../package.json").contributes;
  assert.deepEqual(manifesto.semanticTokenTypes.map(t => t.id), TIPOS);
  for (const [tipo, escopo] of Object.entries(ESCOPOS)) assert.deepEqual(manifesto.semanticTokenScopes[0].scopes[tipo], [escopo]);
  class SemanticTokens {constructor(data) {this.data = data;}}
  class SemanticTokensBuilder {
    constructor() {this.dados = [];}
    push(...args) {this.dados.push(args);}
    build() {return this.dados;}
  }
  const contexto = {subscriptions: []}, logs = [];
  const provedor = registre({extensions, SemanticTokens, SemanticTokensBuilder,
    EventEmitter: class { constructor(){this.event=()=>({dispose(){}});} fire(){} dispose(){} },
    SemanticTokensLegend: class {},
    window: {createOutputChannel: () => ({appendLine: s => logs.push(s), dispose() {}})},
    languages: {registerDocumentSemanticTokensProvider: () => ({dispose() {}})}}, contexto);
  const fonte = 'local a = [=[<b title="🟢]=] .. nome .. [=[fim">é</b>]=]\r\nlocal js=--[[javascript]] "const x=\\u{1f7e2};\\nconst y=2;"';
  const linhas = fonte.split("\n"), inícios = [];
  let offset = 0;
  for (const l of linhas) {inícios.push(offset); offset += l.length + 1;}
  const documento = {version: 1, getText: () => fonte,
    lineAt: n => ({text: linhas[n].replace(/\r$/, "")}),
    positionAt(p) {let line = inícios.findLastIndex(i => i <= p); return {line, character: p - inícios[line]};}};
  const tokens = await provedor.provideDocumentSemanticTokens(documento, {isCancellationRequested: false});
  assert.equal(logs.length, 0, logs.join("\n"));
  assert(tokens.length > 10);
  let anterior = 0;
  for (const [line, char, length, tipo] of tokens) {
    const início = inícios[line] + char;
    assert(início >= anterior && length > 0 && tipo >= 0 && tipo < TIPOS.length);
    assert(char + length <= documento.lineAt(line).text.length);
    anterior = início + length;
  }
  const p = fonte.indexOf("fim");
  assert(tokens.some(([line,char,len,tipo]) => inícios[line]+char <= p && p < inícios[line]+char+len && TIPOS[tipo] === "santafeEmbeddedString"));
  assert.equal(await provedor.provideDocumentSemanticTokens(documento, {isCancellationRequested: true}), undefined);
  const pendente = provedor.provideDocumentSemanticTokens(documento, {isCancellationRequested: false});
  documento.version++;
  assert.equal(await pendente, undefined);
  contexto.subscriptions.forEach(d => d.dispose());
  assert.equal(tipoDosEscopos(["source.js", "comment.block.js", "punctuation.definition.comment.js"]), "santafeEmbeddedComment");
  registro.dispose();
  console.log(`Concatenações: ${total} verificações + API, UTF-16, cancelamento e 3000 fragmentos: ok`);
})().catch(e => {console.error(e); process.exitCode = 1;});
