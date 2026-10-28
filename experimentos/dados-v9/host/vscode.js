"use strict";
// Testes no Extension Host real. Não são captura/inspeção de pixels.
const v=require('vscode'), assert=require('assert'), fs=require('fs'), path=require('path');
const pause=ms=>new Promise(r=>setTimeout(r,ms));
exports.run=async(laboratorio)=>{
 // Permite repetir a mesma bateria pela cópia de desenvolvimento já confiável,
 // sem desabilitar Workspace Trust ao lançar outro perfil do editor.
 const root=laboratorio || v.workspace.workspaceFolders[0].uri.fsPath;
 assert(path.basename(root).startsWith('santafe-dados8-host-'));
 const results={editor:v.version,grupos:[],limite:'Sem inspeção de pixels',resultado:'falhou'};
 const save=()=>fs.writeFileSync(path.join(root,'vscode-dados9-resultado.json'),JSON.stringify(results,null,2));
 const group=(name)=>results.grupos.push(name);
 const errors=doc=>v.languages.getDiagnostics(doc.uri).filter(d=>d.severity===v.DiagnosticSeverity.Error);
 const wait=async(test)=>{for(let i=0;i<120;i++){if(test())return;await pause(100);}assert(test(),'tempo esgotado');};
 let doc, original;
 const replace=async(document,text)=>{
  const e=new v.WorkspaceEdit();e.replace(document.uri,new v.Range(document.positionAt(0),document.positionAt(document.getText().length)),text);
  assert(await v.workspace.applyEdit(e));
 };
 async function tokens(document){
  const legend=await v.commands.executeCommand('vscode.provideDocumentSemanticTokensLegend',document.uri);
  const sem=await v.commands.executeCommand('vscode.provideDocumentSemanticTokens',document.uri);
  assert(sem&&sem.data.length,'tokens ausentes');
  let line=0,char=0,out=[];
  for(let i=0;i<sem.data.length;i+=5){const [dl,dc,len,t]=sem.data.slice(i,i+4);line+=dl;char=dl?dc:char+dc;out.push({line,char,len,type:legend.tokenTypes[t]});}
  return out;
 }
 try{
  doc=await v.workspace.openTextDocument(path.join(root,'visual.fé'));original=doc.getText();
  await v.window.showTextDocument(doc,{preview:false});
  assert.equal(doc.languageId,'santafe-dados');
  const ext=v.extensions.getExtension('santafe.santafe-dados-experimental');
  assert.equal(ext.packageJSON.version,'0.0.9');results.extensão=ext.packageJSON.version;
  const api=await ext.activate();await wait(()=>api.estadoSLS().pronto);
  results.sls=api.estadoSLS().informação;assert.equal(results.sls.version,'1.0.0-dados.9');group('extensão e SLS dados.9 carregados');
  await pause(600);assert.equal(errors(doc).length,0);
  const ts=await tokens(doc);results.tokens=ts;
  const type=(needle,text=original,list=ts)=>{const p=doc.positionAt(text.indexOf(needle));return list.find(t=>t.line===p.line&&t.char<=p.character&&p.character<t.char+t.len)?.type;};
  for(const needle of ['prefixo-','-final'])assert.equal(type(needle),'santafeEmbeddedString',needle);
  assert.equal(type('retomado'),'santafeEmbeddedComment');
  assert.equal(type('const pronto'),'santafeEmbeddedStorage');
  assert.equal(type('data-id'),'santafeEmbeddedAttribute');group('HTML e JS: estado atravessa concatenações e níveis diferentes');
  for(const needle of ['®variável e Ⓡ{título}','[1, nulo]','mostre(página'])assert(!String(type(needle)).startsWith('santafeEmbedded'),needle);
  group('não vaza HTML/JS para bruto comum, listas ou código');
  const position=needle=>doc.positionAt(original.lastIndexOf(needle));
  const rename=await v.commands.executeCommand('vscode.executeDocumentRenameProvider',doc.uri,position('variável ..'),'pessoa');
  const edits=rename.get(doc.uri);assert(edits.length>=3);
  assert(edits.every(e=>doc.getText(e.range)==='variável'));
  assert(!edits.some(e=>e.range.start.line===original.slice(0,original.indexOf('®variável e')).split('\n').length-1));
  group('rename inclui gabarito e exclui bruto literal');
  const config=v.workspace.getConfiguration('santafeDados');
  assert.equal(config.get('highlight.embeddedPalette'),'suave');
  assert((await v.commands.getCommands()).includes('santafeDados.paletaEmbutida'));group('paleta suave habilitada e comando registrado');
  // Edição parcial real: fechamento incorreto, depois reparo.
  const at=original.indexOf('local bruto = [==[')+'local bruto = ['.length;
  const e=new v.WorkspaceEdit();e.insert(doc.uri,doc.positionAt(at),'=');assert(await v.workspace.applyEdit(e));
  await wait(()=>errors(doc).length>0);await replace(doc,original);await wait(()=>errors(doc).length===0);
  group('diagnóstico incremental de delimitador e recuperação');
  const edited=original.replace('data-id="7"','data-id="7" data-novo="sim"');await replace(doc,edited);
  assert.equal(type('data-novo',edited,await tokens(doc)),'santafeEmbeddedAttribute');
  await replace(doc,original);group('realce acompanha atributo inserido ao vivo');
  const data=await v.workspace.openTextDocument(path.join(root,'exemplo.onfé'));
  await v.window.showTextDocument(data,{preview:false});assert.equal(data.languageId,'onfe-experimental');
  const before=data.getText();await pause(600);assert.equal(errors(data).length,0);
  await replace(data,before+'\nimporte "nao-execute"');await wait(()=>errors(data).length>0);
  await replace(data,before);await wait(()=>errors(data).length===0);group('ONFÉ bruto/listas aceitos, código recusado, recuperação');
  await v.window.showTextDocument(doc,{preview:false});
  assert.equal(doc.getText(),original);assert.equal(fs.readFileSync(path.join(root,'visual.fé'),'utf8'),original);
  results.resultado='ok';save();console.log('VSCODE_DADOS9_HOST_OK',results.grupos.length);
 }catch(e){results.falha=e.stack;save();throw e;}
 finally{if(doc&&original&&doc.getText()!==original)await replace(doc,original);}
};
