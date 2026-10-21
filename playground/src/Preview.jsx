import React from 'react';
import {hasSourceLocation} from './diagnostics.mjs';

const display = value => typeof value === 'string' ? value : JSON.stringify(value);
const count = (n, label) => `${n} ${label}${n === 1 ? '' : 's'}`;
export default function Preview({result, status, mode, onSourceLocation, onRetry}) {
  const done = ['done', 'checked', 'failed-request'].includes(status);
  const tested = status === 'done' && mode === 'test';
  const ready = status === 'done' && result?.ok && mode === 'run';
  const checked = status === 'checked' && result?.ok;
  const linted = status === 'done' && mode === 'lint' && result?.ok;
  const failed = done && result && !result.ok;
  const title = mode === 'check' ? 'Program check' : mode === 'lint' ? 'Code warnings' : mode === 'test' ? 'Program tests' : mode === 'format' ? 'Format source' : 'Results';
  const statusLabel = status === 'running' ? 'Working…' : status === 'stale' ? 'Run to update' : failed ? 'Needs a correction' : checked ? 'Check passed' : linted ? (result.warnings?.length ? 'Review warnings' : 'No warnings found') : tested ? (result.total ? 'Tests passed' : 'No tests declared') : ready ? 'Run complete' : 'Waiting for a program';
  function diagnostics(items, advisory = false) {
    return items.map((error,index)=><article className={`diagnostic${advisory ? ' advisory' : ''}`} key={index}>
      <p className="error-code">{error.code}{error.source_name && error.source_name !== '<program>' ? ` · ${error.source_name}` : ''}{error.output_path ? ` · output ${error.output_path}` : error.data_path ? ` · input ${error.data_path}` : error.line ? ` · line ${error.line}, column ${error.column}` : ''}</p>
      <h3>{error.message}</h3>
      {error.source_line ? <pre>{error.source_line}{'\n'}{' '.repeat(Math.max(0,Math.min((error.column || 1)-1,200)))}^</pre> : null}
      {hasSourceLocation(error) ? <button className="source-jump" onClick={()=>onSourceLocation(error.line,error.column,error.source_name || error.source_file)}>Go to {error.source_name && error.source_name !== '<program>' ? error.source_name : 'source'} line {error.line}</button> : null}
      {error.call_trace?.length ? <ol className="call-trace" aria-label="Function call trace">{error.call_trace.map((frame,i)=><li key={i}><button onClick={()=>onSourceLocation(frame.line,frame.column,frame.source_name)}>{frame.function} · {frame.source_name || '<program>'}:{frame.line}</button></li>)}</ol> : null}
    </article>);
  }
  return <section className="preview" aria-label="Preview results" aria-live="polite" aria-busy={status === 'running'}>
    <div className="preview-header"><h2>{title}</h2><span className={`status ${ready || checked || (tested && result?.ok && result.total) ? 'ready' : failed ? 'failed' : ''}`}><i />{statusLabel}</span></div>
    {linted ? <div className="diagnostics"><p className="result-count">{count((result.warnings || []).length, 'warning')}</p>{diagnostics(result.warnings || [], true)}<p className="empty-copy">These warnings can help you find type errors and unused code. This check does not run your program. No warnings does not prove that the program is correct. Run tests and check the result.</p></div>
      : checked ? <div className="preview-empty"><p>Your program passed its checks.</p><span>Syntax, names, supplied input and contract definitions were checked. Annotations, calculations and emitted outputs are checked when execution reaches them. Choose Find warnings, Run preview, or Run tests.</span></div>
      : tested ? <div className="result-body"><p className="result-count">{result.passed || 0} passed · {result.failed || 0} failed · {result.total || 0} tests</p>
        {result.tests?.length ? result.tests.map((item,index)=><article className="test-result" key={index}><h3>{item.ok ? '✓' : '×'} {item.name}</h3>{item.source_name && item.source_name !== '<program>' ? <p className="proposal-provenance">{item.source_name}</p> : null}{diagnostics(item.diagnostics || [])}</article>) : <><p className="empty-copy">No test blocks ran. Add a <code>test "description":</code> block with <code>require</code> expectations.</p>{diagnostics(result.diagnostics || [])}</>}
        <p className="empty-copy">Tests run isolated expectations. The main program's effects do not execute.</p></div>
      : ready ? <><p className="result-count">{count((result.values || []).length,'value')} · {count(result.proposals.length,'proposal')} · {count(result.notes.length,'note')}</p><div className="result-body">
        {(result.values || []).map((value,index)=><article className="emitted-value" key={index}><h3>Value {index+1}</h3><pre>{JSON.stringify(value,null,2)}</pre></article>)}
        {result.proposals.map(proposal=><article className="proposal" key={proposal.id}><h3>{proposal.action}</h3><p className="proposal-provenance">{proposal.rule ? `Rule: ${proposal.rule}` : 'Top-level program'}{proposal.source?.line ? <> · <button onClick={()=>onSourceLocation(proposal.source.line,proposal.source.column,proposal.source.source_name)}>Source line {proposal.source.line}</button></> : null}</p>
          {typeof proposal.fields.explanation === 'string' ? <p className="proposal-explanation">{proposal.fields.explanation}</p> : null}
          {Array.isArray(proposal.fields.evidence) && proposal.fields.evidence.every(item=>typeof item === 'string') ? <ol className="proposal-evidence">{proposal.fields.evidence.map((step,i)=><li key={i}>{step}</li>)}</ol> : null}
          <dl>{Object.entries(proposal.fields).filter(([key,value])=>!(key === 'explanation' && typeof value === 'string') && !(key === 'evidence' && Array.isArray(value) && value.every(item=>typeof item === 'string'))).map(([key,value])=><div className="field-row" key={key}><dt>{key}</dt><dd>{display(value)}</dd></div>)}</dl><details className="proposal-details"><summary>Proposal ID and JSON</summary><p>{proposal.id}</p><pre>{JSON.stringify(proposal,null,2)}</pre></details></article>)}
        {result.notes.length ? <div className="notes"><span className="note-label">Notes</span>{result.notes.map((note,index)=><p key={index}>{note.message}</p>)}</div> : null}
        {!result.values?.length && !result.proposals.length && !result.notes.length ? <p className="empty-copy">The program finished with no values, proposals or notes.</p> : null}
        {result.stats?.duplicates_collapsed ? <p className="dedup-note">{count(result.stats.duplicates_collapsed,'duplicate proposal')} collapsed in this preview.</p> : null}
      </div></> : failed ? <div className="diagnostics" role="alert">{diagnostics(result.diagnostics || [])}<p className="empty-copy">{status === 'failed-request' ? 'Your draft is safe. Retry when the interpreter is ready.' : 'No outputs were produced. Correct the reported problem and try again.'}</p>{status === 'failed-request' ? <button onClick={onRetry}>Retry</button> : null}</div>
      : <div className="preview-empty"><p>Your program is ready.</p><span>Run to see structured values, proposals and notes. Run tests to execute declared expectations.</span></div>}
  </section>;
}
