import yaml
import logging

def run_pipeline(args):
    # Загрузка конфига
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)
    # Оверрайды из args
    if args.input:
        config["input_dir"] = args.input
    # Настройка логирования
    logging.basicConfig(level=config["log_level"], filename="cache/logs/pipeline.log")
    logging.info("Пайплайн запущен")
    # Здесь вызовы этапов (добавим позже)
    logging.info("Пайплайн завершен")