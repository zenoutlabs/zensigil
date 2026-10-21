# Decimal helpers take and return decimal TEXT, explicitly.
# Ordinary numeric operators retain their usual integer/float behavior.
let discounted = dec_mul("19.99", "0.9")
emit {
    exact_sum: dec_add("0.1", "0.2"),
    discounted: discounted,
    rounded_price: dec_round(discounted, 2),
    one_third: dec_div("1", "3", 6)
}

test "Exact decimal sum":
    require dec_add("0.1", "0.2") == "0.3", "Expected exact decimal text."

test "Half-even rounding":
    require dec_round("2.345", 2) == "2.34", "Even tie should round down."
    require dec_round("2.355", 2) == "2.36", "Odd tie should round up."

test "Canonical decimal comparison":
    require dec_compare("1.20", "1.2") == 0, "Equivalent decimal values."
