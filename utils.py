import pathlib


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_error(message: str) -> None:
    print(bcolors.FAIL, 'Error: ', message, bcolors.ENDC)


def change_ext(file, ext):
    return '.'.join(file.split('.')[:-1]) + '.' + ext


def get_ext(file):
    return pathlib.Path(file).suffix


def get_filename(file: str) -> str:
    return pathlib.Path(file).stem


def read_file(filename: str) -> str:
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read()


def write_file(filename: str, data, mode: str = 'w', encoding: str = 'utf-8') -> None:
    with open(filename, mode, encoding=encoding) as file:
        file.write(data)
