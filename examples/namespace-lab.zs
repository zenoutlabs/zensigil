# Two libraries can use the same private helper name.
use "lib/metric.zs" as metric
use "lib/imperial.zs" as imperial

let distances: list<number> = [1, 2, 3]
emit {meters: map(distances, metric.to_meters), feet: map(distances, imperial.to_feet)}

test "Independent public APIs":
    require metric.to_meters(2) == 2000, "Metric API should use its own helper."
    require imperial.to_feet(2) == 6, "Imperial API should use its own helper."
