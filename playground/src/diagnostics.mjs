// Sidecar diagnostics use line 1 as a placeholder, not a source-code location.
export function hasSourceLocation(diagnostic) {
  return Number.isInteger(diagnostic.line) && diagnostic.line > 0
    && typeof diagnostic.source_line === 'string' && diagnostic.source_line.length > 0;
}
