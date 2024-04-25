import argparse
import time


def print_numbers(upto: int):
    for i in range(1, upto + 1):
        print(i)
        time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--upto", type=int)
    args = parser.parse_args()

    print_numbers(args.upto)
