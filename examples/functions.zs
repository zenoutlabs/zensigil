fn factorial(n):
    when n <= 1:
        return 1
    return n * factorial(n - 1)

say "5 factorial is " + text(factorial(5))
