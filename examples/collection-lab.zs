# General data analysis, with domain data passed explicitly.
emit count_by(people, fn (person) => person.team)
emit map(group_by(people, fn (person) => person.team).design, fn (person) => person.name)
emit partition([1, 2, 3, 4, 5], fn (n) => n % 2 == 0)
emit flat_map(people, fn (person) => person.skills)

test "Grouping preserves source order":
    let grouped = group_by([1, 2, 3, 4], fn (n) => choose n % 2 == 0 then "even" otherwise "odd")
    require grouped.odd == [1, 3], "Odd numbers remain in input order."
    require find_index([3, 6, 9], fn (n) => n > 4) == 1, "First match is at index 1."
