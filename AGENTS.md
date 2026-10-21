# Working on ZenSigil

Read `docs/language.md` before changing language behavior. Keep the lexer/parser,
binding checker, runtime, and interface layers understandable and separate.
The language core must stay domain-neutral. No Python eval/exec, shell execution,
implicit network access, or importing arbitrary host objects from a .zs program.

Use synthetic data. `propose` collects reviewable descriptions; it never executes
external actions. Do not imply within-preview deduplication is persistent idempotency.

For language changes, add expected behavior to the specification and an independent
regression case, then run `python3 -m unittest discover -s tests -v`. For UI changes,
run `npm ci` as needed and `npm run build` in playground/, then inspect the browser.
Python runtime stays standard-library-only unless a dependency has a clear benefit.
Keep generated web assets and demo copies in sync using the playground build command.

For AI-authored .zs programs, use `docs/ai-reference.md`; check and run each program
against a known input, and compare the result to explicit expected proposals.

Use short sentences and common words in new user documentation. Keep technical
names when needed. Aim for ASD-STE100 writing principles. Do not claim formal
compliance without a controlled-language review.
