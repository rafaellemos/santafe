"use strict";
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'../..'),base=path.join(root,'dist/candidato-dados-v22/editores/vscode');
const tm=require(path.join(base,'vendor/vscode-textmate')),onig=require(path.join(base,'vendor/vscode-oniguruma'));
const {recorte}=require(path.join(base,'realce-embutido'));
(async()=>{
 await onig.loadWASM(fs.readFileSync(path.join(base,'vendor/vscode-oniguruma/release/onig.wasm')));
 const registry=new tm.Registry({onigLib:Promise.resolve({createOnigScanner:s=>new onig.OnigScanner(s),createOnigString:s=>new onig.OnigString(s)}),
 loadGrammar:async scope=>{const f=path.join(base,'syntaxes',scope==='source.onfe'?'onfe.tmLanguage.json':'santafe.tmLanguage.json');return tm.parseRawGrammar(fs.readFileSync(f,'utf8'),f);}});
 let count=0;
 function scopesAt(grammar,text,target){
  const at=text.indexOf(target);assert(at>=0);let off=0,stack=tm.INITIAL;
  for(const line of text.split('\n')){
   const r=grammar.tokenizeLine(line,stack);stack=r.ruleStack;
   for(const t of r.tokens)if(off+t.startIndex<=at&&off+t.endIndex>at)return t.scopes.join(' ');
   off+=line.length+1;
  }
  throw new Error(target);
 }
 for(const scope of ['source.santafe-dados','source.onfe']){
  const grammar=await registry.loadGrammar(scope);
  for(const n of [1,2,3,9]){
   const eq='='.repeat(n),body='🟢 ®variável Ⓡ{1+2} `` \\n ]'+ '='.repeat(n+1)+']';
   const source='[ '+ '['+eq+'['+body+'\nsegunda linha'+']'+eq+']'+',nulo ]';
   for(const word of ['®variável','Ⓡ{1+2}','segunda linha']){
    const s=scopesAt(grammar,source,word);assert(s.includes('string.quoted.other.raw'),s);assert(!s.includes('interpolation'),s);count++;
   }
   const after=scopesAt(grammar,source,'nulo');assert((after.includes('constant.language')||after.includes('keyword.control'))&&!after.includes('string'),after);count++;
   const ranges=recorte('local x='+source).literais;assert.equal(ranges.length,1);
   assert.equal(ranges[0].partes.filter(p=>p.buraco).length,0);count++;
  }
 }
 const grammar=await registry.loadGrammar('source.santafe-dados');
 for(const [text,word,yes,no] of [
  ['local x=[[1],[2]]','1','constant.numeric','string'],
  ['--[==[ ®nome ]=] ]==]\nlocal x=1','®nome','comment.block','interpolation'],
  ['local x=`®variável Ⓡvariável`','Ⓡvariável','interpolation','raw'],
  ['local x=[==[a]=]b\nresto','resto','string.quoted.other.raw','interpolation'],
  ['local x=``; local y=7','7','constant.numeric','string']]){
    const s=scopesAt(grammar,text,word);assert(s.includes(yes)&&!s.includes(no),s);count++;
 }
 registry.dispose();console.log('TEXTMATE_DELIMITADORES8_OK',count);
 // Verifica o contrato da extensão Prism do manual, sem alegar UI de navegador.
 const vm=require('vm');let pattern;
 const P={languages:{'santafé':{},insertBefore:(name,key,entries)=>{pattern=entries['raw-string'].pattern;return {};}}};
 vm.runInNewContext(fs.readFileSync(path.join(root,'experimentos/dados-v8/prism-dados8.js'),'utf8'),{window:{Prism:P}});
 for(const source of ['[=[®literal]=]','[==[a]=]b]==]','[===[a\n``]===]'])assert.equal(pattern.exec(source)[0],source);
 assert(!pattern.test('[[1],[2]]'));assert(!pattern.test('``texto``'));
 console.log('PRISM_DELIMITADORES8_OK',5);
})().catch(e=>{console.error(e);process.exitCode=1;});
