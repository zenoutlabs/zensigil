# Typed state supports ordinary iterative algorithms.
fn gcd(a: integer, b: integer) -> integer:
    require a >= 0 and b >= 0, "Use nonnegative integers."
    var left: integer = a
    var right: integer = b
    while right != 0:
        let remainder = left % right
        set left = right
        set right = remainder
    return left

fn factorial(n: integer) -> integer:
    require n >= 0 and n <= 30, "Use n from 0 to 30."
    var answer: integer = 1
    for value in range(1, n + 1):
        set answer = answer * value
    return answer

emit {gcd: gcd(84, 30), factorial: factorial(6)}

var odd_total: integer = 0
for value in range(1, 20):
    when value % 2 == 0:
        continue
    when value > 7:
        break
    set odd_total = odd_total + value
emit odd_total

test "Euclidean algorithm":
    require gcd(84, 30) == 6, "Expected gcd 6."
    require gcd(0, 9) == 9, "Zero boundary failed."

test "Factorial boundaries":
    require factorial(0) == 1, "Expected empty product 1."
    require factorial(6) == 720, "Expected 720."
