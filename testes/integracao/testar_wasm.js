"use strict";
/* Executa a mesma ponte web, com DOM mínimo, sem rede nem navegador. */
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const assert = require('assert');
const root = path.resolve(__dirname, '../../src');
const output = {textContent: ''};
let done = false;
const timeout = setTimeout(() => { throw new Error('timeout WebAssembly'); }, 30000);
const Module = {
  wasmBinary: fs.readFileSync(path.join(root, 'santafe.wasm')),
  onRuntimeInitialized() {
    assert.strictEqual(Module.ccall('sf_init', 'number', [], []), 0);
    for (const code of [
      'garanta(_VERSÃO == "Santafé 2.0"); garanta(tipo(verdadeiro) == "lógico")',
      'garanta(tamanho("é👩🏽‍💻क्ष") == 3); garanta(octetos("é") == 2)',
      'garanta(colar.junte("\\0", "a", "b") == "a\\0b")',
      'garanta(tabela.maiorÍndice({[9007199254740993]=1}) == 9007199254740993)',
      'garanta(json.cod(json.matrizVazia) == "[]")',
      'local _AMBIENTE={valor=42, garanta=garanta}; garanta(valor == 42)'
    ]) assert.strictEqual(Module.ccall('sf_run_code', 'number', ['string'], [code]), 0, code + '\n' + output.textContent);
    done = true; clearTimeout(timeout);
    console.log('WebAssembly: versão, lógico, ambiente, grafemas, octetos, JSON, índices e separador: ok');
  }
};
const context = {Module, console, window: {}, WebAssembly, TextDecoder, TextEncoder,
  URL, setTimeout, clearTimeout, performance, Uint8Array, ArrayBuffer,
  fetch: async url => {
    assert(String(url).endsWith('/santafe.wasm'));
    return new Response(fs.readFileSync(path.join(root, 'santafe.wasm')), {headers: {'Content-Type': 'application/wasm'}});
  },
  document: {currentScript: {src: 'file://' + root + '/santafe.js'}, getElementById: () => output}};
vm.runInNewContext(fs.readFileSync(path.join(root, 'santafe.js'), 'utf8'), context);
