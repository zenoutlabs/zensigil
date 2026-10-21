# General data analysis with reusable callbacks.
let events = [{name: "Amber", points: 4}, {name: "Blue", points: 7}, {name: "Coral", points: 7}]
let points = fn (event) => event.points
emit {
    running: scan([4, 7, 7], 0, fn (total, value) => total + value),
    total: sum_by(events, points),
    winner: max_by(events, points).name,
    first_each_score: map(unique_by(events, points), fn (event) => event.name),
    labels: frequencies(["ready", "waiting", "ready"]),
    flattened: flatten([[1, 2], [], [3]]),
    scores: record_from_entries(map(events, fn (event) => [event.name, event.points]))
}

test "Stable tie selection":
    let tied = [{name: "First", points: 7}, {name: "Second", points: 7}]
    require max_by(tied, fn (event) => event.points).name == "First", "Equal keys retain the first item."
