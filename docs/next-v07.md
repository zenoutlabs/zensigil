# ZenSigil 0.7: the next useful developer milestone

The six requested prompts share one outcome: a developer can get a correct result,
understand a failure, share a runnable project, and send useful feedback.
We selected 24 outcomes. This is fewer than 40–50 because the other needs either
work already or require a separate design. The count includes documentation and proof.

| # | Outcome | Acceptance evidence |
|---|---|---|
| 1 | Audit 45 language and adoption needs | adoption-audit-v07.md separates working, partial, missing, unnecessary |
| 2 | Check the main claims against source | reality-check-v07.md distinguishes evidence and limits |
| 3 | Select project input data | Manifest data path is bounded and used by run/check/lint |
| 4 | Select project input contracts | Manifest contract is applied before execution |
| 5 | Select project proposal contracts | Invalid output discards the result |
| 6 | Keep explicit input overrides | A flag takes precedence; a bad override does not fall back |
| 7 | Export runnable projects | pack accepts a directory; portable output matches the project |
| 8 | Protect project input files | Output cannot replace the manifest, source, tests, modules, or declared inputs |
| 9 | Fix invalid manifest failures | Wrong field types return diagnostics, without a Python traceback |
| 10 | Fix output symlink-loop failures | Reproduction returns E_OUTPUT and preserves files |
| 11 | Improve the new-project starter | Runnable source, tests, local instructions, and Python environment/cache ignore rules |
| 12 | Prove fresh setup and a useful task | Isolated installed package; expected result; export/reopen |
| 13 | Check known annotation errors | Advisory type pass for known values; runtime stays authoritative |
| 14 | Check known conditions and operators | Definite misuse produces a source warning without evaluation |
| 15 | Check known function calls and returns | Explicit signatures and module identities are respected |
| 16 | Limit inference and warning work | Unknown values remain unknown; no function execution |
| 17 | Show editor warnings at correct severity | LSP warnings are distinct from blocking errors |
| 18 | Test real editor behavior | State exactly which real-host assertions passed or were blocked |
| 19 | Show warnings in the playground | Find warnings calls the same lint API and offers source navigation |
| 20 | Preserve portable compatibility | Supported old files normalize to 0.7 in Python and JavaScript |
| 21 | Improve defect reports | Setup and language inconsistency forms request small reproductions |
| 22 | Prepare a small developer trial | Five tasks/reports; proposed five $20 payments; no public payment promise |
| 23 | Prepare accurate public copy | Website/bio text says experimental and states observed limits |
| 24 | Verify and deliver the release | Full checks, artifacts, clean-source comparison, and recorded release evidence |

The final results and any incomplete checks belong in [release evidence](release-evidence-v07.md).

## Scope and completion plan

The scope is local developer use of ZenSigil. Keep the core independent of any
business domain. Keep evaluation local and bounded. Do not add network access,
package-registry credentials, or a new execution backend in this milestone.

1. Inspect the 0.6 source and claims: complete.
2. Implement project adoption and type advice: complete.
3. Review defects and check the integrated release: complete locally.
4. Publish the tested source and release files: verify against the public release.
5. Run an independent developer trial: proposed; owner selection and payment terms remain open.

Completion requires the full regression suite, installed-package checks, the first
useful task, browser checks, and exact source/release-file comparison. Remote CI
results must be read from the actual run. Record all limits in the release evidence.
