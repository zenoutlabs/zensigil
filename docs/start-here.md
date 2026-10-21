# Your first 20 minutes with ZenSigil

You have a real small programming language: source code has its own grammar, is
parsed into a structure, and is executed according to explicit rules. It is a
prototype with a deliberately small scope. You do not need to understand every
interpreter file before trying these exercises.

## 1. Say something

Start the playground using the README. Choose **Hello, ZenSigil**. You will see:

```text
let name = "Gregory"
say "Hello, " + name + ". Welcome to ZenSigil."
```

`let` names a value. `say` adds a note to the preview. `+` joins two strings.
Change `Gregory` to `Nikko and Tyler`, then click **Run preview**. You changed a
program in your own language and ran it through its interpreter.

## 2. Understand the stock example

Choose **Stock review**, click **Run preview**, and open **Input data**. The input contains five made-up
products. A17 has 15 units in stock and sells 4 units daily. Its coverage is:

```text
15 / 4 = 3.75 days
```

The rule selects products below 14 days of stock. To reach 30 days, A17 needs:

```text
4 * 30 - 15 = 105 additional units
```

The program records a proposal. It does not place an order.

In Input data, change `policy.review_below_days` from `14` to `3`. Run it again: neither A17 (3.75 days)
nor B24 (exactly 3 days) is below 3, so there are no reorder proposals. D09 still
has missing sales data and still produces its explanatory note. This is a useful
boundary test: `<` means strictly less than, not less than or equal to.

Change the review threshold back to 14. In the data, change A17's `stock` from `15` to `60`. At four
units per day, it now has 15 days of stock, so only B24 should be proposed.

## 3. Break something and fix it

Choose **A helpful error** and click Run preview. The program tries to read `item.stock`, but the input
contains only a SKU. The error names the field and record and points to the source.
Although an earlier line proposed a review, the failed preview returns no proposals.

Add the missing field in **Input data**:

```json
{"item": {"sku": "A17", "stock": 42}}
```

Run again. You should see one review proposal and the note `Stock is 42`.

## 4. See how the core stays general

Choose **Support triage**. This uses the same `for`, `when` and `propose` constructs
with tickets instead of inventory. No change to the interpreter is required.

Choose **Pure functions**. `factorial(5)` returns 120. A function takes values,
calculates something and returns a value. In this version it cannot propose actions
or write notes; those effects stay visible in the calling program.

## 5. Explain what you built

An accurate introduction is:

> I'm developing ZenSigil, an experimental language for readable workflow rules,
> with AI assistance. It has a working interpreter, a local playground and tests.
> Examples cover stock review, support triage, collections and reusable functions.
> It currently previews proposed actions; real integrations come later.

Try to answer these five questions in your own words:

1. What is the difference between a program's code and its input data?
2. Why does `5 + "3"` fail instead of guessing what you meant?
3. What happens if a field is missing halfway through a run?
4. Why do stable proposal IDs alone not stop duplicate real orders?
5. Why can a support workflow use the same core as an inventory workflow?

## Save and share a program

Give the program a name and choose **Save program**. It is stored in this browser.
Reload, then choose it under **Open saved**. A recovered draft is marked unsaved so
you can explicitly keep it. Use **Export program** to download a `.sigil.json` file
containing code, raw input and contract. Someone else can use **Import program**
to open it on their own machine; they choose Run preview when ready. Exported files
are the backup/sharing route if browser storage is cleared or you change the local
address/port. Unsaved changes trigger a Save / Discard / Cancel choice before opening.

## See validation before running

In Stock review input, change A17 stock to `-1` and B24 daily_sales to `"two"`.
Run preview. You should see both input paths and no proposals. Fix those values.
Then set `policy.target_days` to `7` while review_below_days stays `14`: the program
stops with a clear `require` message explaining the conflicting policy. Restore 30.
The contract and require instruction work for any program, including Support triage.

## What to learn next in Python

Read one function at a time. Start with `run()` in `zensigil/__init__.py`, then
the `when` and `for` cases in `Runtime.block()` in `zensigil/runtime.py`. Learn
Python dictionaries, lists, functions, exceptions and loops as you encounter them.
Then read the corresponding cases in `tests/test_language.py`.

For an early real-world test, show the synthetic stock example to Nikko and Tyler.
Ask them to explain it back, change one threshold themselves, and identify missing
business conditions. That feedback is more useful at this stage than adding many
new syntax features.
