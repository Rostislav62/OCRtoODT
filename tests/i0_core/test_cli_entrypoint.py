# Путь: test_cli_entrypoint.py
import pytest
from ocrtoodt.i0_core.cli_entrypoint import main

def test_cli_help():
    with pytest.raises(SystemExit):  # argparse вызывает exit при --help
        main(["--help"])