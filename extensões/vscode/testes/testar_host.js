"use strict";
// Rodar no Extension Host real com --extensionTestsPath. Nenhuma instalação
// global é alterada. O relatório só contém tipos/posições do fixture público.
const vscode = require("vscode"), assert = require("assert"), path = require("path"), fs = require("fs");
exports.run = async () => {
  const arquivo = path.join(__dirname, "visual-concatenacoes.fé");
  const documento = await vscode.workspace.openTextDocument(arquivo);
  await vscode.window.showTextDocument(documento);
  await vscode.extensions.getExtension("santafe.santafe").activate();
  const legenda = await vscode.commands.executeCommand("vscode.provideDocumentSemanticTokensLegend", documento.uri);
  const resposta = await vscode.commands.executeCommand("vscode.provideDocumentSemanticTokens", documento.uri);
  assert(legenda && resposta?.data?.length, "provedor não registrado no editor real");
  const tokens = [];
  let line = 0, character = 0;
  for (let i = 0; i < resposta.data.length; i += 5) {
    const [deltaLine, deltaChar, length, tipo] = resposta.data.slice(i, i + 4);
    line += deltaLine; character = deltaLine ? deltaChar : character + deltaChar;
    tokens.push({line, character, length, tipo: legenda.tokenTypes[tipo]});
  }
  const texto = documento.getText();
  function em(trecho) {
    const p = documento.positionAt(texto.indexOf(trecho));
    return tokens.find(t => t.line === p.line && t.character <= p.character && p.character < t.character + t.length)?.tipo;
  }
  assert.equal(em("prefixo-"), "santafeEmbeddedString");
  assert.equal(em("-final"), "santafeEmbeddedString");
  assert.equal(em("retomado"), "santafeEmbeddedComment");
  assert.equal(em("const"), "santafeEmbeddedStorage");
  assert.equal(em("detalhe"), undefined);
  assert.equal(em("mostre(página)"), undefined);
  assert.equal(em("®nome"), undefined);
  assert.equal(em("Ⓡ{"), undefined);
  const scratch = await vscode.workspace.openTextDocument({language: "santafe", content: 'local a = [[<b class="a]] .. nome .. [[fim">Oi</b>]]'});
  const antes = await vscode.commands.executeCommand("vscode.provideDocumentSemanticTokens", scratch.uri);
  const offset = scratch.getText().indexOf('fim"') + 4;
  const edição = new vscode.WorkspaceEdit();
  edição.insert(scratch.uri, scratch.positionAt(offset), ' data-ativo="sim"');
  assert(await vscode.workspace.applyEdit(edição));
  const depois = await vscode.commands.executeCommand("vscode.provideDocumentSemanticTokens", scratch.uri);
  assert(depois.data.length > antes.data.length, "o realce não acompanhou a edição do documento");
  assert((await vscode.commands.getCommands()).includes("santafe.paletaEmbutida"));
  const relatório = {versão: vscode.extensions.getExtension("santafe.santafe").packageJSON.version, tokens, ediçãoAoVivo: true, resultado: "ok"};
  if (process.env.SANTAFE_TESTE_RELATORIO) fs.writeFileSync(process.env.SANTAFE_TESTE_RELATORIO, JSON.stringify(relatório, null, 2));
  console.log("Extension Host real: concatenações, provider, curingas e limites: ok");
  if (process.env.SANTAFE_TESTE_VISUAL) {
    const visual = await vscode.workspace.openTextDocument(process.env.SANTAFE_TESTE_VISUAL);
    await vscode.window.showTextDocument(visual);
    await vscode.commands.executeCommand("vscode.provideDocumentSemanticTokens", visual.uri);
    await new Promise(r => setTimeout(r, 30000));
  }
};
