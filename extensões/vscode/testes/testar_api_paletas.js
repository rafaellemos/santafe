"use strict";
const fs=require('fs'), path=require('path'), assert=require('assert');
const raiz=path.resolve(__dirname,'..'), tm=require('../vendor/vscode-textmate'), onig=require('../vendor/vscode-oniguruma');
const {trechosDoHospedeiro,registre,paletas}=require('../aparencia');
const {tipoDosEscopos}=require('../realce-vscode');
(async()=>{
 await onig.loadWASM(fs.readFileSync(path.join(raiz,'vendor/vscode-oniguruma/release/onig.wasm')));
 const registry=new tm.Registry({onigLib:Promise.resolve({createOnigScanner:s=>new onig.OnigScanner(s),createOnigString:s=>new onig.OnigString(s)}),loadGrammar:async()=>JSON.parse(fs.readFileSync(path.join(raiz,'syntaxes/santafe.tmLanguage.json'),'utf8'))});
 const grammar=await registry.loadGrammar('source.santafe');
 function scopes(s,p) {return grammar.tokenizeLine(s,tm.INITIAL).tokens.find(t=>t.startIndex<=p && p<t.endIndex).scopes.join(' ');}
 const itens=require('../api-publica.json').itens;
 for(const i of itens) {
   const s=i.rótulo+'()', p=i.rótulo.length-1;
   assert(/support\.|variable\.(function|other\.member)/.test(scopes(s,p)),i.rótulo+': '+scopes(s,p));
 }
 for(const s of ['local função nome()', 'local f = função()', 'função biblioteca.nome()', 'função objeto:método()'])
   assert(scopes(s,s.indexOf('função')).includes('storage.type.function'),s);
 for(const s of ['local x = "mat.raiz()"', '-- mat.raiz()'])
   assert(!scopes(s,s.indexOf('raiz')).includes('support.function'),s);
 assert(scopes('objeto.mostre()',7).includes('entity.name.function.call'));
 const alias='local redeLocal = importe "rede"; redeLocal.laço()';
 assert(scopes(alias,alias.indexOf('laço')).includes('entity.name.function.call'));
 for(const marca of ['®','Ⓡ']) {
   const s='local x = `Olá '+marca+'nome '+marca+'{mat.raiz(4) + valor + tamanho("a")} fim`';
   const t=trechosDoHospedeiro(s).filter(t=>t.estilo==='marcador');
   assert.deepEqual(t.map(t=>s.slice(t.início,t.fim)),[marca+'nome',marca+'{','}']);
   assert(scopes(s,s.indexOf('mat.raiz')+4).includes('support.function'));
 }
 assert.equal(trechosDoHospedeiro('-- ®{n} função()\nlocal s="Ⓡnome :x() função()"').length,0);
 const nomesUnicode=require('../../testes/identificadores-unicode.json');
 for(const nome of nomesUnicode) for(const marca of ['®','Ⓡ']) {
   const alvo=marca+nome;
   for(const corpo of [alvo+'!', '<b title="'+alvo+'">Oi</b>', '/* js */ const nome="'+alvo+'";']) {
     const s='local x = `🟢 '+corpo+'`', começo=s.indexOf(alvo);
     assert.deepEqual(trechosDoHospedeiro(s).filter(t=>t.estilo==='marcador').map(t=>s.slice(t.início,t.fim)),[alvo]);
     for(let p=começo;p<começo+alvo.length;p++)
       assert(scopes(s,p).includes('variable.parameter.santafe'),nome+' cortado em '+p);
     assert(!scopes(s,começo+alvo.length).includes('variable.parameter.santafe'));
   }
 }
 const adjacentes='local a=`®açãoⓇíndice—®variável!`';
 assert.deepEqual(trechosDoHospedeiro(adjacentes).map(t=>adjacentes.slice(t.início,t.fim)),['®ação','Ⓡíndice','®variável']);
 for(const s of ['local a=`\\®ação \\Ⓡvariável`', 'local a="®ação Ⓡvariável"','local a=`®́nome Ⓡ1nome`'])
   assert.equal(trechosDoHospedeiro(s).length,0,s);
 // Compila a regra da gramática Sublime em Oniguruma, sem substituir o
 // ensaio visual do plugin_host. Os recortes Python são testados à parte.
 const sublime=fs.readFileSync(path.join(raiz,'../sublime/Santafe.sublime-syntax'),'utf8');
 const regra=sublime.split('\n').find(l=>l.includes("match: '[®Ⓡ]["));
 assert(regra,'regra Unicode do Sublime ausente');
 const scanner=new onig.OnigScanner([regra.match(/match: '(.*)'/)[1]]);
 for(const nome of nomesUnicode) for(const marca of ['®','Ⓡ']) {
   const alvo=marca+nome, texto='🟢 '+alvo+'—';
   const captura=scanner.findNextMatchSync(texto,0).captureIndices[0];
   assert.equal(texto.slice(captura.start,captura.end),alvo,'Sublime: '+alvo);
 }
 assert.equal(scanner.findNextMatchSync('®́nome Ⓡ1nome',0),null);
 scanner.dispose();
 const aninhado='local s=`Ⓡ{({x="}"}).x}`';
 assert.deepEqual(trechosDoHospedeiro(aninhado).map(t=>aninhado.slice(t.início,t.fim)),['Ⓡ{','}']);
 // Exercita aplicação/remoção de decorações e mudança de tema/paleta.
 const source='local função f() retorne `<b>Ⓡ{valor}</b>` fim';
 const decorated=new Map(), listeners={}, subscriptions=[];
 const doc={uri:{toString:()=> 'file:test'},languageId:'santafe',version:1,positionAt:x=>x};
 const editor={document:doc,setDecorations:(d,r)=>decorated.set(d,r)};
 let mode='suave', theme='Sublime Monokai';
 const config={get:(k,def)=>k==='highlight.embeddedPalette'?mode:k==='colorTheme'?theme:def};
 const event=n=>f=>{listeners[n]=f;return {dispose(){}}};
 const v={ColorThemeKind:{Light:1},Range:class {constructor(a,b){this.start=a;this.end=b;}},
  window:{activeColorTheme:{kind:2},visibleTextEditors:[editor],createTextEditorDecorationType:o=>({...o,dispose(){}}),
   onDidChangeVisibleTextEditors:event('visible'),onDidChangeActiveColorTheme:event('theme')},
  workspace:{getConfiguration:()=>config,onDidChangeConfiguration:event('config'),onDidChangeTextDocument:event('edit'),onDidCloseTextDocument:event('close')}};
 const a=registre(v,{subscriptions},tipoDosEscopos);
 const at=source.indexOf('<b>');
 a.atualize(doc,source,[{início:at+1,fim:at+2,scopes:['entity.name.tag.html']}]);
 assert([...decorated].some(([d,r])=>d.color===paletas.escura.Tag && r.length));
 assert([...decorated].some(([d,r])=>d.color==='#FD971F' && d.fontStyle==='normal' && r.length===2));
 assert([...decorated].some(([d,r])=>d.color==='#66D9EF' && d.fontStyle==='italic' && r.length));
 mode='tema'; listeners.config({affectsConfiguration:()=>true});
 assert(![...decorated].some(([d,r])=>d.color===paletas.escura.Tag && r.length));
 mode='suave';v.window.activeColorTheme.kind=1;listeners.theme();
 assert([...decorated].some(([d,r])=>d.color===paletas.clara.Tag && r.length));
 theme='Dark+';listeners.config({affectsConfiguration:()=>true});
 assert(![...decorated].some(([d,r])=>d.fontStyle==='italic' && r.length));
 doc.version++;listeners.visible();assert([...decorated.values()].every(r=>r.length===0));
 a.atualize(doc,source,[]);doc.languageId='plaintext';listeners.close(doc);
 assert([...decorated.values()].every(r=>r.length===0));
 subscriptions.forEach(s=>s.dispose());registry.dispose();
 console.log(`API/cores: ${itens.length} entradas, chamadas, isolamento, curingas e paletas reversíveis: ok`);
})().catch(e=>{console.error(e);process.exitCode=1;});
