from porchestrator.parser import parse_orchestrator_config


def run_orchestrator(config_path):
    config = parse_orchestrator_config(config_path)
    print(config)
