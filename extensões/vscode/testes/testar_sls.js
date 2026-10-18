"use strict";
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { EventEmitter } = require('events');
const root = path.resolve(__dirname, '..');
const children = [];
const dispose = () => {};
const vscode = {
  workspace: { isTrusted: true, getConfiguration: () => ({get: (_, d) => d, inspect: () => ({})}) },
  window: { createOutputChannel: () => ({appendLine: dispose, append: dispose}), showWarningMessage: dispose },
  languages: { createDiagnosticCollection: () => ({set: dispose}) }
};
function spawn() {
  const child = new EventEmitter();
  child.stdout = new EventEmitter(); child.stderr = new EventEmitter();
  child.stdin = new EventEmitter(); child.sent = [];
  child.stdin.write = frame => child.sent.push(JSON.parse(frame.split('\r\n\r\n')[1]));
  child.stdin.end = dispose;
  child.kill = () => { child.killed = true; };
  children.push(child); return child;
}
const sandbox = { __dirname: root, module: {exports: {}}, exports: {}, Buffer, process, console, setTimeout, clearTimeout,
  require: name => name === 'vscode' ? vscode : name === 'child_process' ? {spawn} : name.startsWith('./') ? require(path.join(root, name)) : require(name) };
vm.runInNewContext(fs.readFileSync(path.join(root, 'extension.js'), 'utf8') + '\nmodule.exports.ClienteSls = ClienteSls;', sandbox);
const client = new sandbox.module.exports.ClienteSls({subscriptions: []});
client.inicie();
const first = children[0];
client.processe({id: first.sent[0].id, result: {}});
assert(client.pronto);
client.pare(); client.inicie();
const second = children[1];
assert.notStrictEqual(second.sent[0].id, first.sent[0].id);
client.processe({id: second.sent[0].id, result: {}});
assert(client.pronto, 'reinício deve aceitar o novo ID de initialize');
first.emit('close', 0);
assert(client.pronto, 'close atrasado não pode invalidar o processo novo');
client.pare(); vscode.workspace.isTrusted = false; client.inicie();
assert.strictEqual(children.length, 2, 'não executar código de workspace sem confiança');
console.log('VS Code: reinício SLS, eventos atrasados e confiança: ok');
