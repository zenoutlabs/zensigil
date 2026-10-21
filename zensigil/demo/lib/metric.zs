fn factor() -> number:
    return 1000

export fn to_meters(value: number) -> number:
    return value * factor()

test "Conversion":
    require to_meters(2) == 2000, "Two kilometers are 2000 meters."
