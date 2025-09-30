import pytest
from ocrtoodt.0_core.cli_entrypoint import main

def test_cli_basic(capsys):
    # Тест запуска CLI без ошибок
    with pytest.raises(SystemExit):  # argparse.exit
        main(["--help"])
    captured = capsys.readouterr()
    assert "OCRtoODT" in captured.out  # Идеальный продукт: Вывод help