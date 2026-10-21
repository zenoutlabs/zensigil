# Pure functions can be reused by multiple entry programs.
fn mean(items: list) -> number:
    require len(items) > 0, "Mean needs at least one number."
    return sum(items) / len(items)

fn squared(value: number) -> number:
    return value * value

test "Library mean":
    require mean([2, 4, 6]) == 4, "Mean should be 4."
