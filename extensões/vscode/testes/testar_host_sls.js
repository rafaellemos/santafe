"use strict";
// Extension Host real: não é um mock de vscode nem o cliente Python.
const v=require("vscode"),assert=require("assert"),fs=require("fs"),path=require("path");
const pause=ms=>new Promise(r=>setTimeout(r,ms));
exports.run=async()=>{
  const root=v.workspace.workspaceFolders[0].uri.fsPath;
  assert(path.basename(root).startsWith("santafe-host-sls-"),"use workspace temporário do ensaio");
  const source='local função somar(a,b)\nretorne a+b\nfim\nlocal variável=1\nlocal variável=2\nmostre(`®variável Ⓡvariável Ⓡ{somar(variável,2)}`)\nlocal página=[[<b title="antes]] .. variável .. [[depois">Oi</b>]]\nmostre(somar(1,2))\n';
  const file=path.join(root,"ensaio.fé"); fs.writeFileSync(file,source);
  const doc=await v.workspace.openTextDocument(file); await v.window.showTextDocument(doc);
  const ext=v.extensions.getExtension("santafe.santafe"),api=await ext.activate();
  for(let i=0;i<150&&!api.estadoSLS().pronto;i++) await pause(100);
  assert(api.estadoSLS().pronto,"SLS não iniciou");
  assert.equal(api.estadoSLS().informação.version,"1.0.0");
  const p=(s,last=false,delta=0)=>doc.positionAt((last?source.lastIndexOf(s):source.indexOf(s))+delta);
  const def=await v.commands.executeCommand("vscode.executeDefinitionProvider",doc.uri,p("somar",true));
  assert.equal(def.length,1); assert.equal(def[0].range.start.line,0);
  const symbols=await v.commands.executeCommand("vscode.executeDocumentSymbolProvider",doc.uri);
  assert(symbols.some(s=>s.name==="somar"));
  const hover=await v.commands.executeCommand("vscode.executeHoverProvider",doc.uri,p("somar",true));
  assert(hover.length>0);
  const refs=await v.commands.executeCommand("vscode.executeReferenceProvider",doc.uri,p("variável"));
  assert(refs.length>=4);
  const rename=await v.commands.executeCommand("vscode.executeDocumentRenameProvider",doc.uri,p("variável"),"posição");
  const edits=rename.get(doc.uri); assert(edits.length>=4);
  assert(edits.every(e=>doc.getText(e.range)==="variável"));
  const signature=await v.commands.executeCommand("vscode.executeSignatureHelpProvider",doc.uri,p("somar(1,2)",true,8));
  assert.equal(signature.signatures[0].label,"somar(a, b)"); assert.equal(signature.activeParameter,1);
  const formatted=await v.commands.executeCommand("vscode.executeFormatDocumentProvider",doc.uri,{tabSize:2,insertSpaces:true});
  assert(formatted.some(e=>e.newText==="  "));
  const legend=await v.commands.executeCommand("vscode.provideDocumentSemanticTokensLegend",doc.uri);
  const semantic=await v.commands.executeCommand("vscode.provideDocumentSemanticTokens",doc.uri);
  const types=new Set(); for(let i=3;i<semantic.data.length;i+=5) types.add(legend.tokenTypes[semantic.data[i]]);
  assert(types.has("function")); assert(types.has("santafeEmbeddedString"));
  // Edição com dois intervalos: exercita a ordem do lote incremental real.
  const change=new v.WorkspaceEdit(); change.replace(doc.uri,new v.Range(p("variável"),p("variável",false,8)),"fruta");
  change.insert(doc.uri,doc.positionAt(source.length),"\nlocal =\n");
  assert(await v.workspace.applyEdit(change));
  for(let i=0;i<50&&!v.languages.getDiagnostics(doc.uri).length;i++) await pause(100);
  assert(v.languages.getDiagnostics(doc.uri).length>0,"diagnóstico após edição incremental ausente");
  const output={sls:api.estadoSLS().informação,extensão:ext.packageJSON.version,
    definição:true,referências:true,rename:true,signature:true,formatação:true,
    realceCombinado:[...types],incremental:true,resultado:"ok"};
  if(process.env.SANTAFE_TESTE_RELATORIO) fs.writeFileSync(process.env.SANTAFE_TESTE_RELATORIO,JSON.stringify(output,null,2));
  // Não salvar fonte modificado; só o fixture temporário é aberto neste teste.
  await v.commands.executeCommand("workbench.action.revertAndCloseActiveEditor");
  console.log("VS Code host real: SLS, Unicode, realce combinado e edição incremental: ok");
};
