# Functions are values; callbacks receive all the data they use.
fn is_active(person: record) -> boolean:
    return person.active

fn by_name(person: record) -> string:
    return lower(trim(person.name))

fn clean(person: record) -> record:
    return {name: trim(person.name), age: person.age}

fn add_age(total: integer, person: record) -> integer:
    return total + person.age

fn double(value: number) -> number:
    return value * 2

let selected = sort_by(filter(people, is_active), by_name)
emit {people: map(selected, clean), total_age: fold(selected, 0, add_age)}
let calculation: function = double
emit map([2, 4, 6], calculation)

test "Map and fold compose":
    require map([1, 2, 3], double) == [2, 4, 6], "Double each value."
    require fold([{age: 10}, {age: 20}], 0, add_age) == 30, "Add ages."
