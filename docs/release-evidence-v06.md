# ZenSigil 0.6 release evidence

This is an experimental language release, with 45 bounded outcomes tracked in
[next-45-v06.md](next-45-v06.md). Counts include tooling, documentation and delivery;
they are not a claim of 45 new syntax constructs or universal language completeness.

## Local checks — 2026-10-21

- Python 3.9.6: 311 unittest methods passed.
- Python 3.12: the same 311 unittest methods passed.
- Node 22: 47 playground data/request tests passed; production UI build passed.
- Editor client/provider suite: 6 JavaScript tests passed. The Python suite includes
  12 new namespace editor methods and 16 earlier LSP methods.
- All 23 runnable examples match independently specified expected outputs, including
  deliberate error behavior. The two new examples exercise scoped libraries and
  running totals/record construction.
- An isolated installed-wheel smoke covers packaged resources and 23 examples,
  CLI/project tools, portable roundtrips, namespace privacy/callbacks/closure capture,
  transactional REPL behavior, parsed JUnit outcomes, stdio LSP and loopback HTTP.
- Browser verification runs both new examples, executes three module tests, displays
  their source identities, and saves/reopens the full namespaced program.
- Independent module review exercised 20 isolation, export, callback, capture, JSON,
  arity and resource probes. Separate editor and CLI reviews found no remaining
  actionable issues after the JUnit symlink-loop diagnostic fix.

## Package verification

The source ZIP uses fixed metadata and sorted entries; reproducibility is checked
by a second build with identical source bytes and compressor. Release checksums
cover the source ZIP, wheel, local VSIX and 14 portable examples. The verifier
checks archive integrity, package metadata and portable example outputs.

## Publication

The public destination is [zenoutlabs/zensigil](https://github.com/zenoutlabs/zensigil),
corrected by the project owner. Source upload, byte comparison and remote CI results
are recorded when delivery finishes. The complete source is published through the
signed-in owner's GitHub browser session; local Git history is preserved separately.

## Boundaries

The VS Code protocol/provider tests pass, but an actual application-host attempt
from 0.5 stopped at workspace trust without reaching assertions. No full VS Code
application validation is claimed for 0.6. The VSIX is locally packaged and is not
published to the Visual Studio Marketplace. No PyPI publication is claimed.

Member completion resolves directly imported aliases, not arbitrary inferred types.
The REPL replays source under cumulative limits; it is not an incremental VM or
stepping debugger. Runtime annotations are not static inference. Namespace values
remain outside JSON. Bare-import compatibility and newly scoped dependencies are
specified in [compatibility.md](compatibility.md).
