"""Command line entry point"""

import sys


def main():
    """
    Command line entry point.

    Expects two arguments in `sys.argv`:
      - directory where the project stack state files reside in
      - name of the stack
    """
    _, directory, stack = sys.argv
    print(f"hello {directory} {stack}")
