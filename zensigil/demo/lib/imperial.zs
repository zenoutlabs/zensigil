fn factor() -> number:
    return 3

export fn to_feet(value: number) -> number:
    return value * factor()

test "Conversion":
    require to_feet(2) == 6, "Two yards are six feet."
