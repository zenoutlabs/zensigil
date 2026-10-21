# Fixing common errors

Read the message and location first. Source errors point to a line and column.
Input errors point to a JSON path. Output errors point to a proposal field.
A failed run returns no proposals or notes, including ones produced before failure.

| Code or symptom | Likely cause | Try this |
|---|---|---|
| `E_NAME` | A name is misspelled, missing from input, or outside its block. | Match the input key exactly; pass values into functions as arguments. |
| `E_FIELD` | A record lacks a field. | Add a required field, or use `get(record, "key", fallback)` for optional data. |
| `E_TYPE` | A value has the wrong type. | Use `text(3)` to print a number; write a comparison for a condition. |
| `E_INPUT_DATA` | Input violates its contract. | Follow `data_path`, such as `$.books[0].pages`, and correct the value. |
| `E_CONTRACT` | An input contract is malformed. | Use only the keywords in [contracts.md](contracts.md). This is not full JSON Schema. |
| `E_PROPOSAL` | An action is undeclared or its fields violate the proposal contract. | Fix the program or the intended contract; inspect the output path and source line. |
| `E_PROPOSAL_CONTRACT` | The action-to-contract map is malformed. | Each action needs a contract explicitly describing an object. |
| `E_REQUIRE` | A program assertion failed. | Follow its message; it often describes a conflict between two input values. |
| `E_ZERO` | Division by zero. | Check the divisor before dividing. |
| `E_INDEX` | A list index is outside its bounds. | The first index is 0; the last is `len(list) - 1`. |
| `E_PURITY` | A function attempted an effect. | Return a value, then use `say` or `propose` in the calling program. |
| `E_ARITY` | A call has the wrong number of arguments. | Compare the call with the function's parameters. |
| `E_LIMIT` | A size, execution or nesting guardrail was reached. | Reduce the input or simplify the program; avoid unbounded recursion. |
| `E_PROGRAM` | A portable file is malformed or from an unsupported version. | Export a supported `.sigil.json`; see [compatibility.md](compatibility.md). |
| `E_OUTPUT` | A CLI destination could not be written. | Choose a writable new path; use `--force` only for a file you intend to replace. |
| Playground cannot connect | The local server stopped or uses another port. | Start the server and open the exact URL it prints. |
| An old preview disappeared | Source, input or contracts changed. | Run again; old results would describe the previous program. |
| Saved programs are missing | You changed browser, profile, hostname or port. | Return to the original address, or import your exported backup. |

`check` can pass while `run` fails: checks do not evaluate branches, function calls
or assertions. A successful preview is also not a proof that your real-world
requirements are correct.

For syntax errors, check four-space indentation, double-quoted strings, commas,
and matching brackets. For JSON errors, remove comments and trailing commas.
Duplicate JSON keys are rejected by the runtime interfaces rather than choosing one.

For a useful bug report, include a small synthetic program, input, contracts,
expected output, actual diagnostic, and `python3 -m zensigil doctor --json`.
Do not include credentials or private data.
