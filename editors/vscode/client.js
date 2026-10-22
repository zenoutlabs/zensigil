'use strict';
const MAX_BODY = 1024 * 1024;
const MAX_HEADER = 8192;

/** A bounded JSON-RPC stdio transport; no sockets, shell, or external package. */
class Client {
  constructor(child, notify, log = () => {}, stopped = () => {}) {
    this.child = child;
    this.notify = notify;
    this.log = log;
    this.stopped = stopped;
    this.buffer = Buffer.alloc(0);
    this.length = null;
    this.nextId = 0;
    this.pending = new Map();
    this.closed = false;
    this.disposing = false;
    this.stopTimer = null;
    child.stdout.on('data', chunk => this.receive(chunk));
    child.stdout.on('error', error => this.fail(error));
    child.stdout.on('end', () => this.fail(new Error('ZenSigil language server output closed.')));
    child.stderr.on('data', chunk => log(String(chunk).slice(0, 4096)));
    child.stderr.on('error', error => this.fail(error));
    child.on('error', error => this.fail(error));
    child.on('exit', () => this.fail(new Error('ZenSigil language server stopped.'), false));
    child.stdin.on('error', error => this.fail(error));
  }
  send(message) {
    if (this.closed) throw new Error('Language server is unavailable.');
    if (this.child.stdin.writableLength > MAX_BODY * 2) throw new Error('Language server input queue is full.');
    const body = Buffer.from(JSON.stringify(message));
    if (body.length > MAX_BODY) throw new Error('Editor message exceeds 1 MiB.');
    this.child.stdin.write(Buffer.concat([Buffer.from(`Content-Length: ${body.length}\r\n\r\n`), body]));
  }
  notification(method, params) {
    this.send({jsonrpc: '2.0', method, params});
  }
  request(method, params = {}) {
    if (this.closed || this.pending.size >= 128) return Promise.reject(new Error('Language server is unavailable or busy.'));
    const id = ++this.nextId;
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error('ZenSigil editor request timed out.'));
      }, 5000);
      this.pending.set(id, {resolve, reject, timeout});
      try { this.send({jsonrpc: '2.0', id, method, params}); }
      catch (error) { clearTimeout(timeout); this.pending.delete(id); reject(error); }
    });
  }
  receive(chunk) {
    if (this.closed) return;
    this.buffer = Buffer.concat([this.buffer, chunk]);
    try {
      for (;;) {
        if (this.length === null) {
          const end = this.buffer.indexOf('\r\n\r\n');
          if (end < 0) {
            if (this.buffer.length > MAX_HEADER) throw new Error('Oversize language-server headers.');
            return;
          }
          if (end > MAX_HEADER) throw new Error('Oversize language-server headers.');
          const headers = this.buffer.subarray(0, end).toString('ascii').split('\r\n');
          const lengths = headers.filter(line => /^content-length:/i.test(line));
          if (lengths.length !== 1 || !/^content-length: *[0-9]{1,8}$/i.test(lengths[0])) throw new Error('Invalid language-server frame.');
          this.length = Number(lengths[0].split(':')[1]);
          if (this.length < 1 || this.length > MAX_BODY) throw new Error('Oversize language-server message.');
          this.buffer = this.buffer.subarray(end + 4);
        }
        if (this.buffer.length < this.length) return;
        const message = JSON.parse(this.buffer.subarray(0, this.length).toString('utf8'));
        this.buffer = this.buffer.subarray(this.length);
        this.length = null;
        if (message.jsonrpc !== '2.0') throw new Error('Invalid language-server response.');
        if (Object.hasOwn(message, 'id')) {
          const pending = this.pending.get(message.id);
          if (pending) {
            this.pending.delete(message.id);
            clearTimeout(pending.timeout);
            if (message.error) pending.reject(new Error(message.error.message || 'ZenSigil request failed.'));
            else pending.resolve(message.result);
          }
        } else if (typeof message.method === 'string') this.notify(message.method, message.params);
      }
    } catch (error) { this.fail(error); }
  }
  fail(error, kill = true) {
    if (this.closed) return;
    this.closed = true;
    clearTimeout(this.stopTimer);
    this.log(error.message);
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timeout);
      pending.reject(error);
    }
    this.pending.clear();
    this.buffer = Buffer.alloc(0);
    if (kill) this.child.kill();
    this.stopped(error);
  }
  dispose() {
    if (this.closed || this.disposing) return;
    this.disposing = true;
    this.stopTimer = setTimeout(() => this.fail(new Error('ZenSigil language server did not stop in time.')), 1000);
    this.stopTimer.unref?.();
    this.request('shutdown').then(() => this.notification('exit', {})).catch(() => this.child.kill());
  }
}
module.exports = {Client};
