"use strict";
const fs=require('fs'),path=require('path'),assert=require('assert');
const base=path.resolve(__dirname,'../../dist/candidato-dados-v22/editores/vscode');
const tm=require(path.join(base,'vendor/vscode-textmate')),onig=require(path.join(base,'vendor/vscode-oniguruma'));
const app=process.argv[2];
const {realce,recorte}=require(path.join(base,'realce-embutido'));
const {trechosDoHospedeiro}=require(path.join(base,'aparencia'));
(async()=>{
 await onig.loadWASM(fs.readFileSync(path.join(base,'vendor/vscode-oniguruma/release/onig.wasm')));
 const registry=new tm.Registry({onigLib:Promise.resolve({createOnigScanner:s=>new onig.OnigScanner(s),createOnigString:s=>new onig.OnigString(s)}),
 loadGrammar:async scope=>{
  const files={'source.santafe-dados':path.join(base,'syntaxes/santafe.tmLanguage.json'),
   'source.onfe':path.join(base,'syntaxes/onfe.tmLanguage.json'),
   'text.html.basic':path.join(app,'extensions/html/syntaxes/html.tmLanguage.json'),
   'source.js':path.join(app,'extensions/javascript/syntaxes/JavaScript.tmLanguage.json'),
   'source.css':path.join(app,'extensions/css/syntaxes/css.tmLanguage.json')};
  return files[scope]?tm.parseRawGrammar(fs.readFileSync(files[scope],'utf8'),files[scope]):null;
 }});
 const grammar=await registry.loadGrammar('source.santafe-dados');let total=0;
 for(const [text,part,yes,no] of [
  ['local x=[[1,nulo],[]]','[','punctuation.section.list','string'],
  ['local x=[=[®variável]=]','®variável','string.quoted.other.raw','interpolation'],
  ['local x=`®variável Ⓡvariável`','®variável','interpolation',null],
  ['local x=`®variável Ⓡvariável`','Ⓡvariável','interpolation',null],
  ['local x=`Ⓡ{1+2}`','1','constant.numeric',null],
  ['--[[ lista [1] ]]','[1]','comment.block',null],
  ['local x=[=[a\n[1]]=]\nlocal y=[2]','[2]','punctuation.section.list','string'],
 ]){
  const at=text.indexOf(part);let offset=0,stack=tm.INITIAL,scope='';
  for(const line of text.split('\n')){
   const r=grammar.tokenizeLine(line,stack);stack=r.ruleStack;
   for(const t of r.tokens)if(offset+t.startIndex<=at&&offset+t.endIndex>at)scope=t.scopes.join(' ');
   offset+=line.length+1;
  }
  assert(scope.includes(yes),scope);if(no)assert(!scope.includes(no),scope);total++;
 }
 const source=fs.readFileSync(path.join(__dirname,'visual.fé'),'utf8');
 const tokens=await realce(source,s=>registry.loadGrammar(s));
 for(const [part,scope] of [['prefixo-','string'],['-final','string'],['retomado','comment'],['const','storage'],['strong','entity.name.tag']]){
  const p=source.indexOf(part);assert(tokens.some(t=>t.início<=p&&p<t.fim&&t.scopes.some(s=>s.includes(scope))),part);total++;
 }
 const ranges=trechosDoHospedeiro(source);const raw=source.indexOf('®variável permanece');
 assert(!ranges.some(t=>t.início<=raw&&raw<t.fim));total++;
 for(const name of ['variável','variável','índice','ação','𐐀nome']) for(const mark of ['®','Ⓡ']){
  const source='local x=`'+mark+name+'`';const all=recorte(source).literais.flatMap(l=>l.partes.filter(p=>p.buraco));
  assert.equal(all.length,1);assert.equal(source.slice(all[0].início,all[0].fim),mark+name);total++;
 }
 const onfe=await registry.loadGrammar('source.onfe');
 assert(onfe.tokenizeLine('importe',tm.INITIAL).tokens.some(t=>t.scopes.includes('invalid.illegal.onfe')));total++;
 assert(onfe.tokenizeLine('{vazio=[],nulo=nulo}',tm.INITIAL).tokens.length>4);total++;
 registry.dispose();console.log('EDITORES_DADOS2_TEXTMATE_E_EMBUTIDOS_OK',total);
})().catch(e=>{console.error(e);process.exitCode=1;});
