use "lib/statistics.zs"

emit {
    mean: mean(samples),
    squares: map(samples, squared),
    classification: choose mean(samples) >= 10 then "high" otherwise "low"
}

test "Imported functions":
    require squared(5) == 25, "Square should be 25."
    require mean([1, 2, 3]) == 2, "Mean should be 2."
