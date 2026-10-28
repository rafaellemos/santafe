"use strict";

// Recorte léxico antes do TextMate: a linguagem embutida nunca consome os
// delimitadores Santafé. Não há eval, execução de código ou leitura de imports.
const ID = /[\p{L}_][\p{L}\p{M}\p{N}_]*/uy;
const INTERPOLAÇÃO = /[®Ⓡ][\p{L}_][\p{L}\p{M}\p{N}_]*/uy;
const NUM = /(?:0[xX][\da-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/y;
const LONGO = /\[(=*)\[/y;
const BRUTO = /\[(=+)\[/y;
const PRECEDÊNCIA = {ou: 1, e: 2, "<": 3, ">": 3, "<=": 3, ">=": 3, "~=": 3, "==": 3,
  "|": 4, "~": 5, "&": 6, "<<": 7, ">>": 7, "..": 8, "+": 9, "-": 9,
  "*": 10, "/": 10, "//": 10, "%": 10, "^": 12};
const RESERVADAS = new Set("local função fim retorne se então senão para em início enquanto repita até pare vápara".split(" "));
const ESCAPES = {a: "\x07", b: "\b", f: "\f", n: "\n", r: "\r", t: "\t", v: "\v"};
// O empacotador do laboratório liga isto só na extensão isolada.
const DIALETO_DADOS = true;

function recorte(fonte) {
  const literais = [], fluxos = [];
  let i = 0;
  function longo() { LONGO.lastIndex = i; return LONGO.exec(fonte); }
  function bruto() { BRUTO.lastIndex = i; return BRUTO.exec(fonte); }
  function comentário() {
    const começo = i;
    i += 2;
    const abre = longo();
    if (abre) {
      i += abre[0].length;
      const fim = fonte.indexOf("]" + abre[1] + "]", i);
      i = fim < 0 ? fonte.length : fim + abre[0].length;
    } else {
      const fim = fonte.indexOf("\n", i);
      i = fim < 0 ? fonte.length : fim;
    }
    return fonte.slice(começo, i);
  }
  function literal(anotação, profundidade) {
    const início = i, abre = DIALETO_DADOS ? bruto() : longo(), marca = fonte[i];
    const fim = abre ? "]" + abre[1] + "]" : marca;
    i += abre ? abre[0].length : 1;
    const conteúdo = i, partes = [];
    let trecho = i;
    function texto(até) { if (até > trecho) partes.push({início: trecho, fim: até}); }
    while (i < fonte.length) {
      if (fonte.startsWith(fim, i)) break;
      if (!abre && fonte[i] === "\\") {
        i += 1;
        if (fonte[i] === "z") { i += 1; while (/\s/u.test(fonte[i] || "") && i < fonte.length) i++; }
        else if (fonte[i] === "\r" && fonte[i + 1] === "\n") i += 2;
        else i = Math.min(fonte.length, i + 1);
      } else if (!abre && marca === "`" && /[®Ⓡ]/u.test(fonte[i])) {
        INTERPOLAÇÃO.lastIndex = i;
        const variável = INTERPOLAÇÃO.exec(fonte);
        if (fonte[i + 1] === "{" && profundidade < 128) {
          texto(i); const inícioBuraco = i; i += 2;
          código(true, profundidade + 1);
          partes.push({início: inícioBuraco, fim: i, buraco: true}); trecho = i;
        } else if (variável) {
          texto(i); const inícioBuraco = i; i += variável[0].length;
          partes.push({início: inícioBuraco, fim: i, buraco: true}); trecho = i;
        } else i++;
      } else i++;
    }
    texto(i);
    const fechamento = i;
    if (fonte.startsWith(fim, i)) i += fim.length;
    const valor = {tipo: "literal", início, fim: i, conteúdo, fechamento,
      longo: !!abre, anotação, partes};
    literais.push(valor);
    return valor;
  }
  function código(expressão = false, profundidade = 0) {
    const tokens = [];
    fluxos.push(tokens);
    let chaves = 0, anotação = null;
    while (i < fonte.length) {
      if (/\s/u.test(fonte[i])) { i++; continue; }
      if (fonte.startsWith("--", i)) {
        const anotado = /^--\[\[(html|javascript|js)\]\]$/.exec(comentário());
        anotação = anotado ? (anotado[1] === "js" ? "javascript" : anotado[1]) : null; continue;
      }
      if (expressão && fonte[i] === "}" && chaves === 0) { i++; break; }
      if (fonte[i] === "{") chaves++;
      if (fonte[i] === "}") chaves--;
      if (/["'`]/.test(fonte[i]) || (DIALETO_DADOS ? bruto() : longo())) {
        tokens.push(literal(anotação, profundidade)); anotação = null; continue;
      }
      anotação = null;
      const início = i;
      ID.lastIndex = NUM.lastIndex = i;
      const id = ID.exec(fonte), número = id ? null : NUM.exec(fonte);
      const valor = id ? id[0] : número ? número[0] :
        /^(?:\.\.\.|\.\.|==|~=|<=|>=|<<|>>|\/\/)/.exec(fonte.slice(i, i + 3))?.[0] || fonte[i];
      i += valor.length;
      tokens.push({tipo: id ? "nome" : número ? "número" : "sinal", valor, início, fim: i});
    }
  }
  código();
  return {literais, fluxos};
}

// Análise só das expressões necessárias para agrupar '..'. O restante do
// programa continua sob o SLS. Chamadas, índices e comentários não viram texto.
function concatenações(tokens) {
  let i = 0;
  const grupos = [];
  function atom(profundidade) {
    const t = tokens[i];
    if (!t || profundidade > 128 || RESERVADAS.has(t.valor)) return null;
    let nó;
    if (["-", "#", "~", "não"].includes(t.valor)) {
      i++; const operando = expr(11, profundidade + 1);
      return operando ? {tipo: "buraco", início: t.início, fim: operando.fim} : null;
    }
    if (t.valor === "(") {
      i++; nó = expr(0, profundidade + 1);
      if (tokens[i]?.valor !== ")") return null;
      const fim = tokens[i++].fim;
      if (!nó) return null;
      nó = {...nó, início: t.início, fim};
    } else if (t.valor === "{") {
      i++;
      while (i < tokens.length && tokens[i].valor !== "}") {
        const antes = i; expr(0, profundidade + 1); if (antes === i) i++;
      }
      if (tokens[i]?.valor !== "}") return null;
      nó = {tipo: "buraco", início: t.início, fim: tokens[i++].fim};
    } else if (t.tipo === "literal" || t.tipo === "nome" || t.tipo === "número") {
      i++; nó = t.tipo === "literal" ? {tipo: "literal", literal: t, início: t.início, fim: t.fim} : {...t, tipo: "buraco"};
    } else return null;
    while (i < tokens.length) {
      if ([".", ":"].includes(tokens[i].valor) && tokens[i + 1]?.tipo === "nome") {
        i += 2; nó = {tipo: "buraco", início: nó.início, fim: tokens[i - 1].fim};
      } else if (tokens[i].valor === "(" || tokens[i].valor === "[") {
        const fecha = tokens[i++].valor === "(" ? ")" : "]";
        while (i < tokens.length && tokens[i].valor !== fecha) {
          const antes = i; expr(0, profundidade + 1); if (antes === i) i++;
        }
        if (tokens[i]?.valor !== fecha) return nó;
        nó = {tipo: "buraco", início: nó.início, fim: tokens[i++].fim};
      } else break;
    }
    return nó;
  }
  function expr(mínimo = 0, profundidade = 0) {
    let esquerda = atom(profundidade);
    if (!esquerda) return null;
    while (i < tokens.length) {
      const op = tokens[i].valor, prioridade = PRECEDÊNCIA[op];
      if (prioridade === undefined || prioridade < mínimo || profundidade > 128) break;
      i++;
      // Para recortar texto, concatenação pode ser agrupada à esquerda, sem
      // executar nem mudar a associatividade real da linguagem. Evita pilhas
      // proporcionais ao número de fragmentos em páginas grandes.
      const direita = expr(prioridade + (op === "^" ? 0 : 1), profundidade + 1);
      if (!direita) break;
      esquerda = {tipo: op === ".." ? "concat" : "buraco", início: esquerda.início,
        fim: direita.fim, esquerda, direita,
        primeiro: op === ".." ? (esquerda.tipo === "literal" ? esquerda.literal : esquerda.tipo === "concat" && esquerda.primeiro) ||
          (direita.tipo === "literal" ? direita.literal : direita.tipo === "concat" && direita.primeiro) : null};
      if (op === "..") grupos.push(esquerda);
    }
    return esquerda;
  }
  while (i < tokens.length) { const antes = i; expr(); if (i === antes) i++; }
  return grupos;
}

function partesDoGrupo(nó, visitados) {
  const partes = [], pilha = [nó];
  while (pilha.length) {
    const atual = pilha.pop();
    if (atual.tipo === "concat") {
      visitados.add(atual); pilha.push(atual.direita, atual.esquerda);
    } else partes.push(atual.tipo === "literal" ? atual.literal : {buraco: true});
  }
  return partes;
}

function materialize(fonte, partes) {
  let texto = "";
  const mapa = [];
  function adicione(valor, início = -1, fim = -1) {
    texto += valor;
    for (let n = 0; n < valor.length; n++) mapa.push({início, fim});
  }
  for (const literal of partes) {
    if (literal.buraco) { adicione("SANTAFE_HOLE"); continue; }
    for (const parte of literal.partes) {
      if (parte.buraco) { adicione("SANTAFE_HOLE"); continue; }
      for (let p = parte.início; p < parte.fim;) {
        const início = p;
        if (!literal.longo && fonte[p] === "\\") {
          p++;
          const c = fonte[p++];
          if (c === "z") { while (p < parte.fim && /\s/u.test(fonte[p])) p++; continue; }
          if (c === "\r" && fonte[p] === "\n") p++;
          const restante = fonte.slice(p, parte.fim);
          const hex = c === "x" ? /^[\da-fA-F]{2}/.exec(restante) : null;
          const unicode = c === "u" ? /^\{([\da-fA-F]{1,8})\}/.exec(restante) : null;
          if (hex) { p += 2; adicione(String.fromCharCode(parseInt(hex[0], 16)), início, p); }
          else if (unicode && parseInt(unicode[1], 16) <= 0x10ffff) {
            p += unicode[0].length; adicione(String.fromCodePoint(parseInt(unicode[1], 16)), início, p);
          } else if (/\d/.test(c || "")) {
            const decimal = /^\d{1,3}/.exec(fonte.slice(p - 1, parte.fim))[0];
            p += decimal.length - 1; adicione(String.fromCharCode(Number(decimal) % 256), início, p);
          } else adicione(ESCAPES[c] || (c === "\r" ? "\n" : c || ""), início, p);
        } else { p++; adicione(fonte[início], início, p); }
      }
    }
  }
  return {texto, mapa};
}

function documentosEmbutidos(fonte) {
  const {literais, fluxos} = recorte(fonte), usados = new Set(), documentos = [];
  const visitados = new Set(), linguagens = new Map();
  const grupos = fluxos.flatMap(concatenações).sort((a, b) => (b.fim - b.início) - (a.fim - a.início));
  function linguagemDe(primeiro) {
    if (!primeiro) return null;
    if (linguagens.has(primeiro)) return linguagens.get(primeiro);
    const isolado = materialize(fonte, [primeiro]).texto;
    const linguagem = primeiro.anotação ||
      (/<(?:!doctype\b|!--|\/?[a-z][a-z0-9:-]*(?:\s|\/?>))/i.test(isolado.split(/\r?\n/, 1)[0]) ? "html" :
        /^\s*\/\*\s*(?:js|javascript)\s*\*\//.test(isolado) ? "javascript" : null);
    linguagens.set(primeiro, linguagem);
    return linguagem;
  }
  function considere(partes) {
    const reais = partes.filter(p => !p.buraco);
    if (!reais.length || reais.some(p => usados.has(p))) return;
    const linguagem = linguagemDe(reais[0]);
    if (!linguagem) return;
    reais.forEach(p => usados.add(p));
    documentos.push({...materialize(fonte, partes), linguagem});
  }
  grupos.forEach(g => { if (!visitados.has(g) && linguagemDe(g.primeiro)) considere(partesDoGrupo(g, visitados)); });
  literais.forEach(l => considere([l]));
  return documentos;
}

async function realce(fonte, obtenhaGramática, cancelado = () => false) {
  // Limite do realce, não da linguagem. Arquivos enormes mantêm o TextMate
  // Santafé seguro, sem prender o host de extensões ou truncar o programa.
  if (cancelado() || fonte.length > 1000000) return [];
  const resultado = [];
  let linhas = 0;
  for (const documento of documentosEmbutidos(fonte)) {
    const gramática = await obtenhaGramática(documento.linguagem === "html" ? "text.html.basic" : "source.js");
    if (!gramática) continue;
    let pilha = null, offset = 0;
    const começoDocumento = resultado.length;
    for (const linha of documento.texto.split("\n")) {
      if (cancelado()) return [];
      if (linha.length > 20000) { resultado.length = começoDocumento; break; }
      let tokens;
      // Na primeira chamada Oniguruma compila as expressões de forma preguiçosa.
      // Repetir a linha a partir do estado original aquece esse cache; jamais
      // publique um resultado stoppedEarly como se fosse uma linha completa.
      for (let tentativa = 0; tentativa < 4; tentativa++) {
        tokens = gramática.tokenizeLine(linha, pilha, 50);
        if (!tokens.stoppedEarly) break;
        await new Promise(resolve => setImmediate(resolve));
        if (cancelado()) return [];
      }
      if (tokens.stoppedEarly) { resultado.length = começoDocumento; break; }
      pilha = tokens.ruleStack;
      for (const token of tokens.tokens) {
        let anterior = null;
        for (let p = offset + token.startIndex; p < offset + Math.min(linha.length, token.endIndex); p++) {
          const ponto = documento.mapa[p];
          if (!ponto || ponto.início < 0) { anterior = null; continue; }
          if (anterior && ponto.início <= anterior.fim) anterior.fim = Math.max(anterior.fim, ponto.fim);
          else {
            anterior = {início: ponto.início, fim: ponto.fim, scopes: token.scopes};
            resultado.push(anterior);
          }
        }
      }
      offset += linha.length + 1;
      if (++linhas % 64 === 0) await new Promise(resolve => setImmediate(resolve));
    }
  }
  return resultado.sort((a, b) => a.início - b.início || a.fim - b.fim);
}

module.exports = {recorte, documentosEmbutidos, realce};
