CONST = 2

def simple_func(x):
    return x + CONST

def decorator(func):
    def inner(x):
        return func(x + 1)

    return inner

@decorator
def decorated_func(x):
    return x

@decorator
def another_decorated_func(x):
    return x*x