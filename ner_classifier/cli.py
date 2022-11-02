from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from os import getenv


HOME = getenv("HOME")
XDG_CONFIG_HOME = getenv("XDG_CONFIG_HOME", f"{HOME}/.config")


class CLI:
    def __init__(self):
        parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument(
            '-a',
            '--annotations-file',
            required=True,
            type=str,
            help="Annotations file")

        self.parser = parser.parse_args()

    def get_annotations_file(self):
        return self.parser.annotations_file


def main():
    cli = CLI()


if __name__ == "__main__":
    main()
