"use strict";
const fs=require("fs"), path=require("path"), assert=require("assert");
const app=process.argv[2];
const tm=require(path.join(app,"node_modules.asar/vscode-textmate"));
const onig=require(path.join(app,"node_modules.asar/vscode-oniguruma"));
const dir=path.resolve(__dirname,"../../dist/candidato-dados-v1/editores");
(async()=>{
  await onig.loadWASM(fs.readFileSync(path.join(app,"node_modules.asar.unpacked/vscode-oniguruma/release/onig.wasm")));
  const registry=new tm.Registry({
    onigLib:Promise.resolve({createOnigScanner:s=>new onig.OnigScanner(s),createOnigString:s=>new onig.OnigString(s)}),
    loadGrammar:async scope=>{
      const file=path.join(dir,scope==="source.onfe"?"onfe.tmLanguage.json":"santafe-dados.tmLanguage.json");
      return tm.parseRawGrammar(fs.readFileSync(file,"utf8"),file);
    }
  });
  const grammar=await registry.loadGrammar("source.santafe.dados");
  const cases=[
    ["local x=[[1,nulo],[]]", "[", "punctuation.section.list", "string"],
    ["local x=[=[®variável \\n]=]", "®variável", "string.quoted.other.raw", "interpolation"],
    ["local x=`®variável Ⓡvariável`", "®variável", "variable.other.interpolation", null],
    ["local x=`®variável Ⓡvariável`", "Ⓡvariável", "variable.other.interpolation", null],
    ["local x=`Ⓡ{1+2}`", "1", "constant.numeric", null],
    ["--[[ lista [1] ]]", "[1]", "comment.block", null],
    ["local x=[=[bruto\n[1]]=]\nlocal y=[2]", "[2]", "punctuation.section.list", "string"],
  ];
  for(const [text,part,yes,no] of cases){
    const at=text.indexOf(part); let offset=0,stack=tm.INITIAL,scopes;
    for(const line of text.split("\n")){
      const result=grammar.tokenizeLine(line,stack); stack=result.ruleStack;
      for(const token of result.tokens) if(offset+token.startIndex<=at && offset+token.endIndex>at) scopes=token.scopes.join(" ");
      offset+=line.length+1;
    }
    assert(scopes?.includes(yes),`${part}: ${scopes}`);
    if(no) assert(!scopes.includes(no),`${part}: ${scopes}`);
  }
  const onfe=await registry.loadGrammar("source.onfe");
  assert(onfe.tokenizeLine("{lista=[nulo,1]}",tm.INITIAL).tokens.length>1);
  assert(onfe.tokenizeLine("importe",tm.INITIAL).tokens.some(t=>t.scopes.includes("invalid.illegal.onfe")));
  registry.dispose();
  console.log("TEXTMATE_CANDIDATO_OK", cases.length+2);
})().catch(e=>{console.error(e);process.exitCode=1;});
