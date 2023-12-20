import random


def random_int(m: int) -> int:
    print("MAX: " + str(m))
    ret = random.randrange(m)
    print("RANDOM: " + str(ret))
    return ret
