# Interactive ZenSigil

The REPL lets you try real ZenSigil code one cell at a time. Start it with
`zensigil repl`. It uses the same parser, checker and interpreter as saved programs.
The standalone module also works with `python -m zensigil.repl`.

```text
zs> var total = 2
zs> total + 3
VALUE 5
zs> set total = total * 4
zs> total
VALUE 8
zs> fn double(value: number) -> number:
...     return value * 2
...
zs> double(total)
VALUE 16
```

Enter a blank line to submit an indented block or bracketed multiline cell. EOF
also submits a pending cell, then exits; incomplete source reports a diagnostic.
Single-line statements and expressions submit immediately. Empty input is ignored.
An expression is recognized by the **ZenSigil parser** and saved as an `emit`
statement. No Python evaluation, shell command or network request is involved.
Functions remain opaque values: bind a function with `let` and call it, rather
than trying to emit the function itself as JSON.

## Successful and failed cells

Successful cells append to the session's runnable source. A failed check or run
leaves earlier source, variables and successful output unchanged. For example:

```text
zs> var count = 3
zs> when true:
...     set count = 999
...     emit count
...     require false, "Try again"
...
E_REQUIRE ... Try again
zs> count
VALUE 3
```

Previous notes, values and proposals are preserved in the session snapshot but
are not printed again. Only newly appended output is shown. Proposals are still
reviewable data; the REPL does not execute them. A duplicate proposal that the
runtime collapses produces no additional proposal line.

Every candidate uses fixed input data and a fixed supplied module map. The normal
binding rules reject redefinitions and input/function name collisions. A cell
calling an unknown function fails immediately; declaring that function later does
not turn the failed cell into history. Forward references within a complete cell
follow the ordinary language rules. Existing successful source must replay with
an identical output prefix, or the candidate is rejected before committing.

## Commands

| Command | Result |
| --- | --- |
| `:help` | Display usage |
| `:show` | Show accumulated runnable source, including explicit `emit` wrappers for entered expressions |
| `:undo` | Remove the last successful cell and restore the previous result snapshot |
| `:reset` | Clear history and output while retaining input, modules and remaining work allowance |
| `:load "path/to/source.zs"` | Append one explicitly named regular UTF-8 source file as a single cell |
| `:save "path/to/program.sigil.json"` | Create a portable program containing source, fixed input and supplied modules |
| `:quit` | Exit, discarding any unfinished cell |

Commands accept quoted paths containing spaces. They do not expand variables,
`~`, wildcard patterns or shell expressions. Commands other than `:quit` require
finishing or cancelling an unfinished cell first. Ctrl+C cancels pending input.
An interrupt during execution rejects that cell and keeps prior source/output.

`:load` accepts source files only; it does not parse a portable document or discover
files through imports. A `use` declaration needs a module already supplied to the
session. The Python constructor accepts this map explicitly. Source loaded from
disk passes through exactly the same transaction checks as a typed cell.

`:save` **only creates a new file**. There is deliberately no overwrite or force
command, so a source file, existing portable program or symlink cannot be replaced.
The saved program can be imported into the playground or run through the CLI.
It contains the accumulated source, rather than a memory dump or execution history;
reopening it starts a normal deterministic run.

## Replay and resource limits

This implementation replays the accumulated successful source from the beginning
for each new candidate. It is **not an incremental virtual machine**. A later cell
may cost more as history grows, and declarations/loops run again internally even
though prior output is hidden. The language's lack of external execution effects
makes that replay suitable for a small experimentation session.

The default limits are 64 KiB of accumulated UTF-8 source, 256 accepted cells,
100,000 runtime steps per attempt and **1,000,000 steps of cumulative work** per
session. Input, module, JSON, nesting, call-depth and output limits from the core
also apply. Already emitted results still count toward the full program's output
limit. Saving frequently and starting a new session is appropriate for longer work.

Successful attempts charge their actual **whole-program replay** step count. The
public interpreter does not report partial step counts on failure, so a failed or
interrupted execution conservatively consumes its full reserved allowance, plus
the single limit-detection tick. Syntax and binding failures execute no code and
consume no runtime allowance. Failure therefore preserves program state/history,
while the separate work meter can advance. The final step is reserved for detecting
exhaustion, so fewer than two remaining steps cannot begin another attempt.

Undo restores an earlier output prefix and source checkpoint without executing
anything. Undo and reset do **not** refund spent work; exiting and starting a new
session creates a fresh budget. The Python API permits a per-attempt allowance up
to 1,000,000 steps and a cumulative allowance up to 10,000,000 steps, with the same
conservative accounting.

## Embedding and supplied streams

```python
from zensigil.repl import Session

session = Session(
    data={"scores": [2, 3]},
    modules={"math.zs": "fn double(x):\n    return x * 2\n"},
)
assert session.submit('use "math.zs"')["ok"]
result = session.submit("map(scores, double)")
assert result["values"] == [[4, 6]]

snapshot = session.last_result  # A detached copy of all successful output.
source = session.source        # Runnable accumulated source.
history = session.history      # Immutable tuple of accepted source cells.
```

`submit(source, expression=True)` returns `ok`, `diagnostics`, output deltas and
`status`, `cell_count`, `steps_spent` and `remaining_steps`. Set `expression=False`
when accepting source files so an invalid file cannot be reinterpreted as a REPL
expression. `load`, `save`, `undo` and `reset` return the same session metadata.
Invalid constructor input or budget settings raise `ValueError` before a session
starts. Constructor inputs are validated and copied; later caller mutations cannot
change replay semantics. Returned result objects are copies as well.

`main(data=None, modules=None, stdin=None, stdout=None, stderr=None)` supports
ordinary text streams, including `io.StringIO`. Prompts and the introductory banner
appear only when both input and output report a terminal. Piped output contains
`VALUE`, `NOTE` and `PROPOSAL` lines plus explicitly requested command messages.
Errors go to stderr. Exit status is 0 for a clean session, 1 if any submitted cell
or command failed, and 2 for invalid launch input or stream-read errors. Cancelling
unsubmitted input does not count as a failed cell.

The focused regression suite covers transactional mutation and output, function
bindings, frozen inputs/modules, undo/reset, cumulative budgets, parser-only
expression recognition, load/save round trips and overwrite refusal, multiline
input, EOF, interruption and recovery from malformed commands and oversized lines.
