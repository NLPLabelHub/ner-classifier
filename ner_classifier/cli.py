from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from os import getenv
from ner_classifier.project import Project


XDG_CONFIG_HOME = getenv("XDG_CONFIG_HOME", f"{getenv('HOME')}/.config")


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
        parser.add_argument(
            '-c',
            '--config-dir',
            required=False,
            type=str,
            default=XDG_CONFIG_HOME,
            help="Configuration directoy")

        self.parser = parser.parse_args()

    def get_annotations_file(self):
        return self.parser.annotations_file

    def get_config_dir(self):
        return self.parser.config_dir


def main():
    cli = CLI()
    _ = Project(cli.get_annotations_file(), cli.get_config_dir())


if __name__ == "__main__":
    main()
