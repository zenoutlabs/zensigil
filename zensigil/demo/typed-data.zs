# Collection annotations validate all nested values at runtime.
fn first_or_null(items: list<integer>) -> integer | null:
    return choose len(items) > 0 then items[0] otherwise null

let scores: record<list<integer>> = groups
emit {first: first_or_null(scores.alpha), empty: first_or_null([]), total: sum(scores.beta)}

test "An optional result has a defined empty case":
    require first_or_null([]) == null, "An empty list has no first item."
    require first_or_null([4, 5]) == 4, "Expected the first integer."
