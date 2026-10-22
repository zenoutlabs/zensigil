export async function requestProgram(mode, program, {signal, timeoutMs = 15000, fetcher = fetch} = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort(signal?.reason);
  if (signal?.aborted) abort();
  else signal?.addEventListener('abort', abort, {once: true});
  let timedOut = false;
  const timer = setTimeout(() => {timedOut = true; controller.abort();}, timeoutMs);
  const payload = {source: program.source, modules: program.modules || {}};
  if (mode === 'test') {
    payload.tests = program.tests || {};
    if (Object.hasOwn(program, 'entry_path')) payload.entry_path = program.entry_path;
  }
  if (mode !== 'test' && mode !== 'format') payload.data_text = program.data_text;
  if (program.contract_text.trim()) payload.contract_text = program.contract_text;
  if (program.proposal_contract_text.trim()) payload.proposal_contract_text = program.proposal_contract_text;
  try {
    const response = await fetcher(`/api/${mode}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload), signal: controller.signal});
    const body = await response.json();
    if (!response.ok) {
      const error = new Error(body.error || 'The interpreter request failed.');
      error.kind = response.status >= 400 && response.status < 500 ? 'input' : 'connection';
      throw error;
    }
    return body;
  } catch (error) {
    if (timedOut) throw new Error('The interpreter took longer than 15 seconds. Your draft is safe. Retry when the local server is ready.');
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
  }
}
