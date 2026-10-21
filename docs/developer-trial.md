# A small developer trial

Status: proposed. No reward offer is active. No participant has been promised payment.
The owner can approve and fund the trial after reviewing this brief.

## Aim

Find the first problems that a new developer meets. Use people who did not build
ZenSigil. A prepared automated test is not a substitute for this trial.

## Proposed budget

Invite five developers. Reserve $20 for each complete session and report: $100 total.
Pay for the work, not for praise or the number of bugs. A clear report with no defect
still qualifies. Do not offer a bonus for stars, reviews, promotion, or a public post.
Agree on the task, payment method, and completion rule before a participant starts.
Do not collect payment details in a public GitHub issue.

Suggested mix: two Windows users, two macOS users, and one Linux user. Include one
person new to Python tools. Each session should take about 30 minutes. This is a
small usability trial, not a security bounty or a broad security audit.

## Participant task

1. Use the released ZIP or repository. Follow the quickstart from a new folder.
2. Create a project. Run it. Compare the result with the stated expected result.
3. Change an input value. Run the same command again.
4. Add one small function and one test.
5. Put text in a number annotation. Find its warning. Correct the source.
6. Export the project. Run the exported file from a different folder.
7. Give one small report. Use only synthetic data.

Do not require a course. Give the quickstart, reference, and issue links. Let the
participant work without coaching for the first 15 minutes. Record questions that
require help. Do not silently fix the person's environment and call setup a pass.

## Report template

- ZenSigil version and installation route:
- Operating system, Python version, and editor:
- Steps completed without help:
- First unclear instruction or error:
- Small source and JSON input:
- Expected result:
- Actual result:
- Command or clicks that repeat the result:
- One change that would make the task easier:

Attach `zensigil doctor --json` output if useful. Review it before sharing. Do not
attach secrets, private customer data, or a full machine log.

## Review and exit rule

Use one issue per reproducible defect. Label evidence as reproduced, needs input,
design question, or duplicate. Merge duplicate reports without dismissing the tester.
Keep exact expected behavior in a regression test before changing the implementation.

A reasonable pilot target is four of five participants completing the first task
without direct help, with no unresolved data-loss or installation defect. This is
an internal target, not a performance or adoption claim. Report the observed result,
including failures, before deciding on paid advertising.
