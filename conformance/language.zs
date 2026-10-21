# Executable examples of the language's compositional meaning.
fn twice(n: number) -> number:
    return n * 2

fn apply(f: function, value: number) -> number:
    return f(value)

test "Precedence and grouping":
    require 2 + 3 * 4 == 14, "Multiplication binds more tightly."
    require (2 + 3) * 4 == 20, "Parentheses group first."

test "Strict equality":
    require true != 1, "Booleans differ from numbers."
    require {a: [1, 2]} == {a: [1.0, 2]}, "Structural equality."

test "Lazy composition":
    require (null ?? 4) == 4, "Null fallback."
    require (3 ?? (1 / 0)) == 3, "Unused fallback is lazy."
    require (choose true then 7 otherwise 1 / 0) == 7, "Unused branch is lazy."
    require not false and true, "Boolean composition."

test "Lexical local state":
    var counter: integer = 0
    while counter < 3:
        set counter = counter + 1
    require counter == 3, "Explicit state changes."
    when true:
        let counter = 99
        require counter == 99, "Inner binding."
    require counter == 3, "Inner binding did not escape."

test "Functions as arguments":
    let operation: function = twice
    require operation(4) == 8, "Alias call."
    require apply(operation, 5) == 10, "Higher-order parameter."
    require map([1, 2], operation) == [2, 4], "Callback composition."

test "Unicode text and slices":
    require "a🙂z"[1] == "🙂", "Index counts Unicode characters."
    require "a🙂z"[1:3] == "🙂z", "Slice preserves characters."
    require [1, 2, 3][1:] == [2, 3], "Collection slices."

test "Collection meaning":
    require [1, 2] + [3] == [1, 2, 3], "List composition."
    require true not in [1], "Membership is type-aware."
    require "a" in {a: 1}, "Record membership checks keys."
    require unique([1, true, 1.0]) == [1, true], "Unique respects equality."

test "Exact decimal text":
    require dec_add("0.1", "0.2") == "0.3", "Exact decimal sum."
    require dec_round("2.345", 2) == "2.34", "Explicit half-even rounding."
