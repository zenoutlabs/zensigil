# Learn ZenSigil in six small programs

Start `python3 -m zensigil serve --port 8766`, then open
http://127.0.0.1:8766. You need Python 3.9 or newer; no AI subscription or API key
is involved. All examples use made-up data.

## 1. Name a value

```text
let name = "Nikko"
say "Hello, " + name
```

Run this with `{}` as input. You should see the note `Hello, Nikko`.
Change the name to Tyler. `let` names a value; `say` produces a note.
Values cannot be reassigned.

## 2. Make a decision

```text
when pages <= 250:
    say "A short read"
otherwise:
    say "Save it for a longer weekend"
```

Use `{"pages": 250}` as input. The note is `A short read`. Try 251: the other
message appears. `<=` includes the boundary, while `<` does not. Use four spaces
for each indented block and double quotes around text.

## 3. Work through a collection

Choose **Reading list**. Only *The Small Garden* is proposed: it is unfinished
and has 180 pages. *Learning the Night Sky* has 420 pages and *Weekend Sketchbook*
is already finished. Raise `max_pages` from 250 to 500. You should now see two
proposals. The same loop can inspect books, projects, tickets, or records of your own.

## 4. Reuse a calculation

```text
fn remaining(capacity, registered):
    return capacity - registered

say text(remaining(30, 18))
```

The note is `12`. A function takes values and returns a value. It cannot read your
input behind the scenes or create proposals. Pass what it needs as arguments.
`text` converts a number to text explicitly.

## 5. Catch a mistake before it becomes a proposal

Choose **Event capacity**. There is one proposal for S1: 3 extra places need
review. S2 is full; S3 has 12 places available.

Open **Input data** and replace S1's `registered` number with `"many"`.
Run again. The input contract reports the affected field, and no proposals appear.
Restore 23. Then open the proposal contract and change the minimum for
`extra_places_needed` from 1 to 4. Run again: the output fails validation because
3 is below 4. Restore 1.

Input contracts check what comes in. Proposal contracts check what the program
produces. They do not prove the policy is sensible: a human still chooses the rules.

## 6. Share something another person can run

Choose **Project budget**. P1 is 7,500 cents over budget; P2 and P3 are within
budget. This example uses whole cents for exact arithmetic. It supports one
currency per input; it does not convert currencies.

Give it a name, save it, and export its `.sigil.json` file. The file includes
source, data, and both optional contracts. Someone else can import it in the
playground or run:

```sh
python3 -m zensigil run my-program.sigil.json --json
```

`Check program` verifies syntax, names, supplied input and contract definitions.
It does not execute your program. `Run preview` evaluates it and validates its
proposals. Only a successful run produces a downloadable preview.

## Explain it back

Ask Nikko or Tyler to try these tasks without coaching:

1. Change the reading-list page limit and predict the result.
2. Fix the intentionally invalid event registration.
3. Save a program, reload, and reopen it.
4. Explain why an over-budget proposal does not spend money.

Record what was confusing. These are proposed user exercises, not a claim that
either person has tested this release.

Answers: a higher page limit can admit more unread books; registration must be a
whole number; named saves live in this browser and exports are portable backups;
`propose` records a description and has no action executor.
