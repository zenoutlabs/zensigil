'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {EventEmitter} = require('node:events');
const {PassThrough} = require('node:stream');
const {Client} = require('../client');

function child() {
  const process = new EventEmitter();
  process.stdin = new PassThrough();
  process.stdout = new PassThrough();
  process.stderr = new PassThrough();
  process.killed = false;
  process.kill = () => { process.killed = true; process.emit('exit', 1); };
  return process;
}
function frame(value) {
  const body = Buffer.from(JSON.stringify(value));
  return Buffer.concat([Buffer.from(`Content-Length: ${body.length}\r\n\r\n`), body]);
}

test('transport parses split UTF-8 frames and matches responses', async () => {
  const process = child();
  const notices = [];
  const client = new Client(process, (...args) => notices.push(args));
  const request = client.request('initialize', {});
  const raw = frame({jsonrpc: '2.0', id: 1, result: {text: '🌱'}});
  for (const byte of raw) process.stdout.write(Buffer.from([byte]));
  assert.deepEqual(await request, {text: '🌱'});
  const a = frame({jsonrpc: '2.0', method: 'textDocument/publishDiagnostics', params: {uri: 'file:///x.zs', diagnostics: []}});
  const b = frame({jsonrpc: '2.0', method: 'window/logMessage', params: {message: 'checked'}});
  process.stdout.write(Buffer.concat([a, b]));
  assert.equal(notices.length, 2);
  assert.equal(client.pending.size, 0);
  process.kill();
});

test('oversize framing stops the child and rejects outstanding requests', async () => {
  const process = child();
  const client = new Client(process, () => {});
  const pending = client.request('initialize');
  const rejection = assert.rejects(pending, /Oversize/);
  process.stdout.write('Content-Length: 1048577\r\n\r\n');
  await rejection;
  assert.equal(process.killed, true);
  assert.equal(client.buffer.length, 0);
});

test('duplicate lengths and invalid JSON do not leave timers or requests pending', async () => {
  for (const raw of ['Content-Length: 2\r\nContent-Length: 2\r\n\r\n{}', 'Content-Length: 1\r\n\r\n{']) {
    const process = child();
    const client = new Client(process, () => {});
    const pending = assert.rejects(client.request('initialize'));
    process.stdout.write(raw);
    await pending;
    assert.equal(client.pending.size, 0);
    assert.equal(process.killed, true);
  }
});

test('server errors are request errors while notifications remain usable', async () => {
  const process = child();
  const client = new Client(process, () => {});
  const pending = assert.rejects(client.request('textDocument/formatting'), /invalid source/);
  process.stdout.write(frame({jsonrpc: '2.0', id: 1, error: {code: -32602, message: 'invalid source'}}));
  await pending;
  assert.equal(client.closed, false);
  client.notification('textDocument/didClose', {textDocument: {uri: 'file:///x.zs'}});
  process.kill();
});

test('input failure kills the child, clears requests, and notifies the host once', async () => {
  const process = child();
  const stopped = [];
  const client = new Client(process, () => {}, () => {}, error => stopped.push(error.message));
  const pending = assert.rejects(client.request('initialize'), /broken input/);
  process.stdin.emit('error', new Error('broken input'));
  await pending;
  assert.equal(process.killed, true);
  assert.equal(client.pending.size, 0);
  assert.equal(stopped.length, 1);
});

test('graceful disposal is idempotent and cleans the stop timer on exit', async () => {
  const process = child();
  const stopped = [];
  const client = new Client(process, () => {}, () => {}, error => stopped.push(error.message));
  let raw = '';
  process.stdin.on('data', chunk => { raw += chunk.toString(); });
  client.dispose(); client.dispose();
  assert.equal((raw.match(/shutdown/g) || []).length, 1);
  process.stdout.write(frame({jsonrpc: '2.0', id: 1, result: null}));
  await new Promise(resolve => setImmediate(resolve));
  assert.match(raw, /exit/);
  process.emit('exit', 0);
  assert.equal(client.closed, true);
  assert.equal(client.pending.size, 0);
  assert.equal(process.killed, false);
  assert.equal(stopped.length, 1);
});

test('output closure and pipe errors cannot leave a live unusable child', async () => {
  for (const [stream, event] of [['stdout', 'end'], ['stdout', 'error'], ['stderr', 'error']]) {
    const process = child();
    const client = new Client(process, () => {});
    const pending = assert.rejects(client.request('initialize'));
    process[stream].emit(event, new Error('closed pipe'));
    await pending;
    assert.equal(process.killed, true);
    assert.equal(client.pending.size, 0);
  }
});
