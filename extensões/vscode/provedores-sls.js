"use strict";
// Somente conversão de protocolo. O servidor nunca aplica edições no disco.
const documento=d=>({textDocument:{uri:d.uri.toString()}});
const ponto=(d,p)=>({...documento(d),position:{line:p.line,character:p.character}});
const intervalo=(v,r)=>new v.Range(r.start.line,r.start.character,r.end.line,r.end.character);
const localização=(v,l)=>new v.Location(v.Uri.parse(l.uri),intervalo(v,l.range));
async function peça(c,m,p,t) {
  try { return await c.solicite(m,p,t); }
  catch(e) { c.saída.appendLine(`${m}: ${e.message}`); return undefined; }
}
function textoSeguro(v,texto) {
  const md=new v.MarkdownString(); md.appendText(String(texto || ""));
  md.isTrusted=false; return md;
}
async function complete(v,c,d,p,t) {
  const resposta=await peça(c,"textDocument/completion",ponto(d,p),t);
  const itens=Array.isArray(resposta)?resposta:resposta?.items;
  return itens?.map(i=>{
    const item=new v.CompletionItem(i.label,Math.max(0,(i.kind||3)-1));
    item.detail=i.detail;
    if(i.documentation) item.documentation=textoSeguro(v,i.documentation.value||i.documentation);
    if(i.insertText) item.insertText=i.insertText;
    return item;
  });
}
async function hover(v,c,d,p,t) {
  const r=await peça(c,"textDocument/hover",ponto(d,p),t);
  return r ? new v.Hover(textoSeguro(v,r.contents?.value||r.contents),r.range&&intervalo(v,r.range)) : undefined;
}
async function definição(v,c,d,p,t) {
  const r=await peça(c,"textDocument/definition",ponto(d,p),t);
  return r ? (Array.isArray(r)?r.map(l=>localização(v,l)):localização(v,r)) : undefined;
}
async function símbolos(v,c,d,t) {
  const r=await peça(c,"textDocument/documentSymbol",documento(d),t);
  const converta=s=>{
    const value=new v.DocumentSymbol(s.name,s.detail||"",Math.max(0,s.kind-1),intervalo(v,s.range),intervalo(v,s.selectionRange));
    value.children=(s.children||[]).map(converta); return value;
  };
  return r?.map(converta);
}
function edição(v,c,valor) {
  const edit=new v.WorkspaceEdit();
  for (const change of valor?.documentChanges||[]) {
    if (!change.textDocument || change.kind) throw new Error("SLS: operação de arquivo não permitida.");
    const uri=change.textDocument.uri, versão=change.textDocument.version;
    const aberto=c.documentos.get(uri);
    if (versão!=null && (!aberto || aberto.version!==versão))
      throw new Error("O documento mudou durante a análise. Repita a operação.");
    edit.set(v.Uri.parse(uri),(change.edits||[]).map(e=>new v.TextEdit(intervalo(v,e.range),e.newText)));
  }
  return edit;
}
function registre(v,contexto,c) {
  const sel={language:"santafe"}, sub=contexto.subscriptions;
  sub.push(v.languages.registerReferenceProvider(sel,{
    async provideReferences(d,p,context,t) {
      if(!c.suporta("referencesProvider")) return;
      const r=await peça(c,"textDocument/references",{...ponto(d,p),context},t);
      return r?.map(l=>localização(v,l));
    }
  }),v.languages.registerDocumentHighlightProvider(sel,{
    async provideDocumentHighlights(d,p,t) {
      if(!c.suporta("documentHighlightProvider")) return;
      const r=await peça(c,"textDocument/documentHighlight",ponto(d,p),t);
      return r?.map(h=>new v.DocumentHighlight(intervalo(v,h.range),Math.max(0,(h.kind||1)-1)));
    }
  }),v.languages.registerRenameProvider(sel,{
    async prepareRename(d,p,t) {
      if(!c.suporta("renameProvider")) throw new Error("SLS sem suporte a renomeação.");
      const r=await c.solicite("textDocument/prepareRename",ponto(d,p),t);
      if(!r) throw new Error("Não há um símbolo estaticamente seguro nesta posição.");
      return {range:intervalo(v,r.range),placeholder:r.placeholder};
    },
    async provideRenameEdits(d,p,newName,t) {
      if(!c.suporta("renameProvider")) return;
      const r=await c.solicite("textDocument/rename",{...ponto(d,p),newName},t);
      return r ? edição(v,c,r) : undefined;
    }
  }),v.languages.registerSignatureHelpProvider(sel,{
    async provideSignatureHelp(d,p,t) {
      if(!c.suporta("signatureHelpProvider")) return;
      const r=await peça(c,"textDocument/signatureHelp",ponto(d,p),t);
      if(!r) return;
      const h=new v.SignatureHelp(); h.activeSignature=r.activeSignature||0; h.activeParameter=r.activeParameter||0;
      h.signatures=(r.signatures||[]).map(s=>{
        const sig=new v.SignatureInformation(s.label,s.documentation&&textoSeguro(v,s.documentation.value||s.documentation));
        sig.parameters=(s.parameters||[]).map(p=>new v.ParameterInformation(p.label)); return sig;
      }); return h;
    }
  },"(",","),v.languages.registerDocumentFormattingEditProvider(sel,{
    async provideDocumentFormattingEdits(d,options,t) {
      if(!c.suporta("documentFormattingProvider")) return;
      const version=d.version, r=await peça(c,"textDocument/formatting",{...documento(d),options},t);
      return d.version===version ? r?.map(e=>new v.TextEdit(intervalo(v,e.range),e.newText)) : undefined;
    }
  }),v.languages.registerFoldingRangeProvider(sel,{
    async provideFoldingRanges(d,context,t) {
      if(!c.suporta("foldingRangeProvider")) return;
      const r=await peça(c,"textDocument/foldingRange",documento(d),t);
      return r?.map(f=>new v.FoldingRange(f.startLine,f.endLine));
    }
  }),v.languages.registerSelectionRangeProvider(sel,{
    async provideSelectionRanges(d,positions,t) {
      if(!c.suporta("selectionRangeProvider")) return;
      const r=await peça(c,"textDocument/selectionRange",{...documento(d),positions:positions.map(p=>({line:p.line,character:p.character}))},t);
      const conv=s=>new v.SelectionRange(intervalo(v,s.range),s.parent&&conv(s.parent));
      return r?.map(conv);
    }
  }),v.languages.registerCodeActionsProvider(sel,{
    async provideCodeActions(d,range,context,t) {
      if(!c.suporta("codeActionProvider")) return;
      const r=await peça(c,"textDocument/codeAction",{...documento(d),range:{start:range.start,end:range.end},context:{diagnostics:[]}},t);
      return r?.map(a=>{
        const action=new v.CodeAction(a.title,v.CodeActionKind.QuickFix);
        action.edit=edição(v,c,a.edit); return action;
      });
    }
  },{providedCodeActionKinds:[v.CodeActionKind.QuickFix]}),v.languages.registerWorkspaceSymbolProvider({
    async provideWorkspaceSymbols(query,t) {
      if(!c.suporta("workspaceSymbolProvider")) return;
      const r=await peça(c,"workspace/symbol",{query},t);
      return r?.map(s=>new v.SymbolInformation(s.name,Math.max(0,s.kind-1),s.containerName||"",localização(v,s.location)));
    }
  }));
  const watcher=v.workspace.createFileSystemWatcher("**/{*.fé,*.fe,.santafe/estado.json}");
  let timer; const changes=new Map();
  const change=(uri,type)=>{
    changes.set(uri.toString(),{uri:uri.toString(),type}); clearTimeout(timer);
    timer=setTimeout(()=>{
      if(c.pronto) c.notifique("workspace/didChangeWatchedFiles",{changes:[...changes.values()].slice(0,512)});
      changes.clear();
    },100);
  };
  sub.push(watcher,watcher.onDidCreate(u=>change(u,1)),watcher.onDidChange(u=>change(u,2)),
    watcher.onDidDelete(u=>change(u,3)),{dispose(){clearTimeout(timer);changes.clear();}},
    v.workspace.onDidChangeWorkspaceFolders(()=>c.reinicie()));
}
module.exports={registre,complete,hover,definição,símbolos,edição,peça};
