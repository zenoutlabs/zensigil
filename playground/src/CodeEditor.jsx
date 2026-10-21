import React, { forwardRef, useImperativeHandle, useRef } from 'react';

import {sourceSelection} from './programs.mjs';

const TOKENS = /("(?:[^"\\]|\\.)*"|#[^\n]*|\b(?:rule|for|in|when|otherwise|let|fn|return|say|propose|require|var|set|while|break|continue|choose|then|emit|test|use|as|export|and|or|not)\b|\b(?:true|false|null)\b|\b\d+(?:\.\d+)?\b)/g;
const KEYWORDS = /^(rule|for|in|when|otherwise|let|fn|return|say|propose|require|var|set|while|break|continue|choose|then|emit|test|use|as|export|and|or|not)$/;

function highlight(source) {
  return source.split(TOKENS).map((part, index) => {
    const type = part.startsWith('#') ? 'comment' : part.startsWith('"') ? 'string'
      : KEYWORDS.test(part) ? 'keyword' : /^(true|false|null)$/.test(part) ? 'literal'
        : /^\d/.test(part) ? 'number' : '';
    return <span className={type} key={index}>{part}</span>;
  });
}

export default forwardRef(function CodeEditor({ source, onChange, filename, disabled }, ref) {
  const paint = useRef(null);
  const gutter = useRef(null);
  const input = useRef(null);

  useImperativeHandle(ref, () => ({focusLine(line, column) {
    const range = sourceSelection(source, line, column);
    const element = input.current;
    element.focus(); element.setSelectionRange(range.start, range.end);
    element.scrollTop = Math.max(0, range.index * parseFloat(getComputedStyle(element).lineHeight) - element.clientHeight / 3);
    element.scrollLeft = 0;
    paint.current.scrollTop = element.scrollTop; paint.current.scrollLeft = 0;
    gutter.current.scrollTop = element.scrollTop;
  }}), [source]);

  function scroll(event) {
    paint.current.scrollTop = event.currentTarget.scrollTop;
    paint.current.scrollLeft = event.currentTarget.scrollLeft;
    gutter.current.scrollTop = event.currentTarget.scrollTop;
  }

  function keydown(event) {
    // Tab keeps normal keyboard navigation; type spaces to indent.
    if (event.key === 'Enter' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.nativeEvent.isComposing) {
      const { selectionStart: start, selectionEnd: end, value } = event.currentTarget;
      const line = value.slice(0, start).split('\n').at(-1);
      const indent = line.match(/^ */)[0] + (line.trimEnd().endsWith(':') ? '    ' : '');
      event.preventDefault();
      onChange(value.slice(0, start) + '\n' + indent + value.slice(end));
      requestAnimationFrame(() => input.current?.setSelectionRange(start + indent.length + 1, start + indent.length + 1));
    }
  }

  return <section className="editor" aria-label="Program editor">
    <div className="editor-title"><span>{filename}</span><span>ZenSigil</span></div>
    <div className="editor-body">
      <pre className="line-numbers" ref={gutter} aria-hidden="true">
        {Array.from({ length: Math.max(21, source.split('\n').length) }, (_, index) => index + 1).join('\n')}
      </pre>
      <div className="code-content">
        <pre className="code-paint" ref={paint} aria-hidden="true">{highlight(source)}{'\n'}</pre>
        <textarea ref={input} aria-label="ZenSigil source code" value={source}
          onChange={event => onChange(event.target.value)} onScroll={scroll} onKeyDown={keydown}
          spellCheck="false" autoCapitalize="off" autoCorrect="off" wrap="off"
          disabled={disabled} maxLength={65536} />
      </div>
    </div>
  </section>;
});
