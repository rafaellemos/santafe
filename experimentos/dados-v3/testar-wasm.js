'use strict';
// Ponte do portal num DOM mínimo, sem rede. Não é teste visual de navegador.
const fs=require('fs'), vm=require('vm'), path=require('path'), assert=require('assert');
const root=path.resolve(__dirname,'../..'), output={textContent:''};
const cases=[
  'garanta(tipo([])=="lista" e tipo({})=="tabela")',
  'local t={nome=nulo}; garanta(tabela.temChave(t,"nome")); tabela.apague(t,"nome"); garanta(não tabela.temChave(t,"nome"))',
  'local l=[1,nulo,3,nulo]; garanta(#l==4); local n=0; para i,v em ipares(l) início n=n+1 fim; garanta(n==4)',
  'local l=[1,2]; garanta(não proteja(função() l[5]=7 fim)); garanta(#l==2); tabela.apague(l,1); garanta(#l==1 e l[1]==2)',
  'local v=[=[®literal \\n literal]=]; garanta(json.cod(v)==[=["®literal \\\\n literal"]=])',
  'local variável="NFC"; local variável="NFD"; garanta(`®variável Ⓡvariável`=="NFC NFD")',
  'garanta(json.cod(json.decod("[null,{},[],false]"))=="[null,{},[],false]")',
  'garanta(não proteja(json.cod,{[1]="numérico"})); garanta(json.cod({["1"]="texto"})==\'{"1":"texto"}\')',
  'garanta(json.decod("9223372036854775807")==9223372036854775807); garanta(json.cod(9223372036854775807)=="9223372036854775807")',
  'garanta(não proteja(json.decod,\'{"a":null,"a":1}\'))',
  'garanta(tamanho("é👩🏽‍💻क्ष")==3); garanta(octetos("é")==2)',
  'local O=executeArquivo("/onfé.fé"); local x=O.decod(\'{a=[nulo,{},[]],texto=[=[linha \\n]=]}\'); garanta(O.paraJSON(x):procure("null",1,verdadeiro)); garanta(O.decod(O.cod(x)).texto==x.texto)',
  'local O=executeArquivo("/onfé.fé"); garanta(não proteja(O.decod,\'{a=(função() erro("não executar") fim)()}\'))',
  'local x=[]; para i=1,10000 início x[i]=nulo fim; coleteLixo("colete"); garanta(#x==10000 e tabela.temChave(x,10000))',
  'garanta(tipo(depure.lexemas("local x=1"))=="lista"); garanta(json.cod(depure.lexemas("-- vazio"))=="[]")'
];
cases.push(fs.readFileSync(path.join(root,"experimentos/dados-v4/testar-colares.fé"),"utf8").replace("experimentos/dados-v1/onfé.fé","/onfé.fé"));
cases.push('local O=executeArquivo("/onfé.fé"); local ok,f=proteja(O.grave,"/nao-gravar.onfé",{}); garanta(não ok e f:procure("indisponível",1,verdadeiro)); garanta(es.abra("/nao-gravar.onfé","rb")==nulo)');
cases.push(fs.readFileSync(path.join(root,"experimentos/dados-v8/wasm.fé"),"utf8"));
const deadline=setTimeout(()=>{throw Error('tempo limite WebAssembly');},30000);
const Module={
  wasmBinary:fs.readFileSync(path.join(root,'src/santafe.wasm')),
  printErr:()=>{},
  onRuntimeInitialized(){
    assert.strictEqual(Module.ccall('sf_init','number',[],[]),0);
    Module.FS.writeFile('/onfé.fé',fs.readFileSync(path.join(root,'experimentos/dados-v1/onfé.fé')));
    for(const [i,code] of cases.entries()){
      output.textContent='';
      assert.strictEqual(Module.ccall('sf_run_code','number',['string'],[code]),0,`caso ${i+1}: ${code}\n${output.textContent}`);
    }
    assert.notStrictEqual(Module.ccall('sf_run_code','number',['string'],['local x=[1,']),0);
    assert.strictEqual(Module.ccall('sf_run_code','number',['string'],['garanta(#[]==0)']),0);
    clearTimeout(deadline);
    console.log(`WebAssembly dados.23: ${cases.length} casos + recuperação após erro: ok`);
  }
};
vm.runInNewContext(fs.readFileSync(path.join(root,'src/santafe.js'),'utf8'),{
  Module,console,window:{},WebAssembly,TextDecoder,TextEncoder,URL,setTimeout,clearTimeout,
  performance,Uint8Array,ArrayBuffer,
  fetch:async url=>{
    assert(String(url).endsWith('/santafe.wasm'), 'sem acesso a outro recurso');
    return new Response(fs.readFileSync(path.join(root,'src/santafe.wasm')),
                        {headers:{'Content-Type':'application/wasm'}});
  },
  document:{currentScript:{src:'file://'+root+'/src/santafe.js'},getElementById:()=>output}
});
