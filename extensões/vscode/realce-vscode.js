"use strict";

const fs = require("fs");
const path = require("path");
const {realce} = require("./realce-embutido");

// Escopos públicos, traduzidos em tipos exclusivos para não alterar as cores
// semânticas de outros idiomas/extensões. Manifesto e testes usam esta legenda.
const ESCOPOS = {
  santafeEmbeddedTag: "entity.name.tag",
  santafeEmbeddedAttribute: "entity.other.attribute-name",
  santafeEmbeddedComment: "comment",
  santafeEmbeddedString: "string",
  santafeEmbeddedNumber: "constant.numeric",
  santafeEmbeddedConstant: "constant.language",
  santafeEmbeddedKeyword: "keyword.control",
  santafeEmbeddedStorage: "storage.type",
  santafeEmbeddedOperator: "keyword.operator",
  santafeEmbeddedFunction: "entity.name.function",
  santafeEmbeddedType: "entity.name.type",
  santafeEmbeddedSupport: "support.function",
  santafeEmbeddedVariable: "variable.other",
  santafeEmbeddedParameter: "variable.parameter",
  santafeEmbeddedProperty: "variable.other.property",
  santafeEmbeddedEntity: "constant.character.entity",
  santafeEmbeddedPunctuation: "punctuation",
  santafeEmbeddedText: "text.html.basic"
};
const TIPOS = Object.keys(ESCOPOS);

function tipoDosEscopos(scopes) {
  // Comentários e strings devem conservar sua cor também nos delimitadores.
  if (scopes.some(s => s.startsWith("comment"))) return "santafeEmbeddedComment";
  for (const s of [...scopes].reverse()) {
    for (const [prefixo, tipo] of [
      ["entity.name.tag", "Tag"], ["entity.other.attribute-name", "Attribute"],
      ["constant.character", "Entity"], ["string", "String"],
      ["constant.numeric", "Number"], ["constant.language", "Constant"],
      ["storage", "Storage"], ["keyword.operator", "Operator"], ["keyword", "Keyword"],
      ["entity.name.function", "Function"], ["entity.name.type", "Type"],
      ["support", "Support"], ["variable.parameter", "Parameter"],
      ["variable.other.property", "Property"], ["variable", "Variable"]
    ]) if (s === prefixo || s.startsWith(prefixo + ".")) return "santafeEmbedded" + tipo;
  }
  return scopes.some(s => s.startsWith("punctuation")) ? "santafeEmbeddedPunctuation" : "santafeEmbeddedText";
}

async function crieRegistro(extensions) {
  const tm = require("./vendor/vscode-textmate");
  const onig = require("./vendor/vscode-oniguruma");
  await onig.loadWASM(await fs.promises.readFile(path.join(__dirname, "vendor/vscode-oniguruma/release/onig.wasm")));
  const caminhos = new Map();
  // Somente contribuições dos idiomas nativos. Nada vem do projeto editado.
  for (const id of ["vscode.html", "vscode.javascript", "vscode.css"]) {
    const extensão = extensions.getExtension(id);
    for (const g of extensão?.packageJSON?.contributes?.grammars || [])
      caminhos.set(g.scopeName, path.resolve(extensão.extensionPath, g.path));
  }
  return new tm.Registry({
    onigLib: Promise.resolve({createOnigScanner: s => new onig.OnigScanner(s), createOnigString: s => new onig.OnigString(s)}),
    loadGrammar: async scope => {
      const arquivo = caminhos.get(scope);
      return arquivo ? tm.parseRawGrammar(await fs.promises.readFile(arquivo, "utf8"), arquivo) : null;
    }
  });
}

function registre(vscode, contexto, cliente) {
  const aparência = require("./aparencia").registre(vscode, contexto, tipoDosEscopos);
  const legenda = new vscode.SemanticTokensLegend([...TIPOS,"variable","function","parameter"], ["declaration"]);
  let promessa, descartado = false, avisado = false;
  const saída = vscode.window.createOutputChannel("Santafé: realce embutido");
  const mudança=new vscode.EventEmitter();
  const provedor = {
    onDidChangeSemanticTokens:mudança.event,
    async provideDocumentSemanticTokens(documento, cancelamento) {
      const versão = documento.version;
      const cancelado = () => descartado || cancelamento.isCancellationRequested || documento.version !== versão;
      if (cancelado()) return undefined;
      const fonte = documento.getText();
      if (fonte.length > 1000000) return new vscode.SemanticTokens(new Uint32Array());
      try {
        const registro = await (promessa ||= crieRegistro(vscode.extensions));
        const tokens = await realce(fonte, scope => registro.loadGrammar(scope), cancelado);
        if (cancelado()) return undefined;
        aparência.atualize(documento, fonte, tokens);
        const builder = new vscode.SemanticTokensBuilder(legenda);
        const faixas=[];
        if(cliente?.suporta("semanticTokensProvider")) {
          const resposta=await require("./provedores-sls").peça(cliente,"textDocument/semanticTokens/full",
            {textDocument:{uri:documento.uri.toString()}},cancelamento);
          if(cancelado()) return undefined;
          const reservados=[...tokens,...require("./aparencia").trechosDoHospedeiro(fonte)
            .filter(t=>t.estilo==="marcador")].sort((a,b)=>a.início-b.início);
          let linha=0,coluna=0,cursor=0;
          const tipos=cliente.capacidades.semanticTokensProvider.legend?.tokenTypes||[];
          for(let i=0;i+4<(resposta?.data?.length||0);i+=5) {
            const [dl,dc,tamanho,tipo,mod]=resposta.data.slice(i,i+5);
            linha+=dl; coluna=dl?dc:coluna+dc;
            const nome=tipos[tipo],posição=["variable","function","parameter"].indexOf(nome);
            if(posição<0 || linha>=documento.lineCount || tamanho<1) continue;
            const início=documento.offsetAt(new vscode.Position(linha,coluna)),fim=início+tamanho;
            while(cursor<reservados.length && reservados[cursor].fim<=início) cursor++;
            if(reservados[cursor]?.início<fim) continue;
            faixas.push({linha,coluna,tamanho,tipo:TIPOS.length+posição,mod:mod&1});
          }
        }
        let fimAnterior = 0;
        for (const token of tokens) {
          // Escape Unicode pode gerar dois UTF-16 apontando ao mesmo escape.
          // Não sobrepor tokens, e jamais atravessar uma linha na API LSP.
          let início = Math.max(token.início, fimAnterior);
          while (início < token.fim) {
            const posição = documento.positionAt(início);
            const fim = Math.min(token.fim, início + documento.lineAt(posição.line).text.length - posição.character);
            if (fim > início) faixas.push({linha:posição.line,coluna:posição.character,tamanho:fim-início,
              tipo:TIPOS.indexOf(tipoDosEscopos(token.scopes)),mod:0});
            início = fim + 1;
          }
          fimAnterior = Math.max(fimAnterior, token.fim);
        }
        faixas.sort((a,b)=>a.linha-b.linha||a.coluna-b.coluna);
        for(const f of faixas) builder.push(f.linha,f.coluna,f.tamanho,f.tipo,f.mod);
        return builder.build();
      } catch (erro) {
        // Preserva o realce Santafé, sem interromper SLS/conclusões nem abrir
        // avisos a cada edição. Não registrar conteúdo do documento.
        if (!avisado) { saída.appendLine(`Realce HTML/JS indisponível: ${erro.message}`); avisado = true; }
        return new vscode.SemanticTokens(new Uint32Array());
      }
    }
  };
  contexto.subscriptions.push(saída,mudança,
    vscode.languages.registerDocumentSemanticTokensProvider({language: "santafe"}, provedor, legenda),
    {dispose() { descartado = true; promessa?.then(r => r.dispose(), () => {}); }});
  if(cliente) contexto.subscriptions.push(cliente.aoMudarEstado.event(()=>mudança.fire()));
  return provedor;
}

module.exports = {registre, crieRegistro, TIPOS, ESCOPOS, tipoDosEscopos};
