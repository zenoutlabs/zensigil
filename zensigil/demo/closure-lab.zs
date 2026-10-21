# Reuse a calculation with a captured parameter.
fn multiplier(factor: number) -> function:
    return fn (value: number) -> number => value * factor

let triple = multiplier(3)
let selected = filter(numbers, fn (value: number) -> boolean => value >= threshold)
emit map(selected, triple)

test "Capture preserves the original value":
    var offset = 2
    let add_offset = fn (value) => value + offset
    set offset = 100
    require add_offset(5) == 7, "The closure captures 2, not the later 100."

test "A returned function can be called":
    require multiplier(4)(6) == 24, "Expected 24."
