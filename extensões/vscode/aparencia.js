"use strict";

const {recorte} = require("./realce-embutido");
const paletas = require("./paletas.json");

// Somente marcadores e métodos Santafé. Nunca procurar com regex dentro do
// conteúdo de comentários, colares comuns ou documentos HTML/JS virtuais.
function trechosDoHospedeiro(fonte) {
  const {literais, fluxos} = recorte(fonte), resultado = [];
  for (const literal of literais) for (const p of literal.partes) if (p.buraco) {
    if (fonte[p.início + 1] === "{") {
      resultado.push({início:p.início, fim:p.início+2, estilo:"marcador"});
      if (fonte[p.fim-1] === "}") resultado.push({início:p.fim-1, fim:p.fim, estilo:"marcador"});
    } else resultado.push({...p, estilo:"marcador"});
  }
  for (const fluxo of fluxos) for (let i=0; i<fluxo.length; i++) {
    const t=fluxo[i];
    if (t.valor === "função") resultado.push({...t, estilo:"declaração"});
    if (t.valor === ":" && fluxo[i+1]?.tipo === "nome" && fluxo[i+2]?.valor === "(")
      resultado.push({...fluxo[i+1], estilo:"marcador"});
  }
  return resultado;
}

function registre(vscode, contexto, tipoDosEscopos) {
  // Os testes de protocolo não precisam simular uma janela do editor.
  if (!vscode.window.createTextEditorDecorationType) return {atualize() {}};
  const cache=new Map(), tipos=new Map();
  function tipo(cor, fonte="normal") {
    const chave=cor+fonte;
    if (!tipos.has(chave)) {
      // Estilo por tema evita o caminho de métricas que oculta a decoração
      // no renderer 1.142. Cor e normal/italic permanecem explícitos.
      const t=vscode.window.createTextEditorDecorationType({
        color:cor, light:{fontStyle:fonte}, dark:{fontStyle:fonte}
      });
      tipos.set(chave,t); contexto.subscriptions.push(t);
    }
    return tipos.get(chave);
  }
  function desenhe(editor) {
    if (editor.document.languageId !== "santafe") {
      for (const d of tipos.values()) editor.setDecorations(d,[]);
      return;
    }
    const dados=cache.get(editor.document.uri.toString()), grupos=new Map();
    const clara=vscode.window.activeColorTheme.kind === vscode.ColorThemeKind.Light;
    const cfg=vscode.workspace.getConfiguration("santafe",editor.document.uri);
    const monokai=/monokai/i.test(vscode.workspace.getConfiguration("workbench").get("colorTheme",""));
    function adicione(t,cor,fonte="normal") {
      const d=tipo(cor,fonte); if (!grupos.has(d)) grupos.set(d,[]);
      grupos.get(d).push(new vscode.Range(editor.document.positionAt(t.início),editor.document.positionAt(t.fim)));
    }
    if (dados && dados.versão === editor.document.version) {
      if (cfg.get("highlight.embeddedPalette","tema") === "suave") {
        const paleta=paletas[clara ? "clara" : "escura"];
        for (const t of dados.tokens) adicione(t,paleta[tipoDosEscopos(t.scopes).replace("santafeEmbedded","")]);
      }
      for (const t of dados.hospedeiro) {
        if (t.estilo === "marcador") adicione(t,clara ? "#995500" : "#FD971F");
        else if (monokai) adicione(t,"#66D9EF","italic");
      }
    }
    for (const d of tipos.values()) editor.setDecorations(d,grupos.get(d)||[]);
  }
  function redesenhe() { for (const editor of vscode.window.visibleTextEditors) desenhe(editor); }
  contexto.subscriptions.push(
    vscode.window.onDidChangeVisibleTextEditors(redesenhe),
    vscode.window.onDidChangeActiveColorTheme(redesenhe),
    vscode.workspace.onDidChangeConfiguration(e=>{
      if (e.affectsConfiguration("santafe.highlight") || e.affectsConfiguration("workbench.colorTheme")) redesenhe();
    }),
    vscode.workspace.onDidChangeTextDocument(redesenhe),
    vscode.workspace.onDidCloseTextDocument(d=>{cache.delete(d.uri.toString());redesenhe();}),
    {dispose(){cache.clear();}}
  );
  return {atualize(documento,fonte,tokens) {
    cache.set(documento.uri.toString(),{versão:documento.version,tokens,hospedeiro:trechosDoHospedeiro(fonte)});
    redesenhe();
  }};
}
module.exports={registre,trechosDoHospedeiro,paletas};
