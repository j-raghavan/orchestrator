import os
from collections import defaultdict

import yaml


def expand_env_vars(data):
    if isinstance(data, str):
        return os.path.expandvars(data)
    if isinstance(data, dict):
        return {key: expand_env_vars(value) for key, value in data.items()}
    if isinstance(data, list):
        return [expand_env_vars(item) for item in data]
    return data


def resolve_tasks(job, job_cache, job_map, resolved_tasks):
    if job["name"] in job_cache:
        return

    job_cache[job["name"]] = True

    for dependency_name in job.get("needs", []):
        dependency_job = job_map.get(dependency_name)
        if dependency_job and dependency_job.get("enabled", False):
            resolve_tasks(dependency_job, job_cache, job_map, resolved_tasks)

    if "run" in job:
        run_tasks = job["run"]
        for priority in ("p0", "p1", "p2"):
            tasks = run_tasks.get(priority, [])
            if tasks:
                resolved_tasks[priority].extend(tasks)


def load_yaml_chunks(file):
    loader = yaml.SafeLoader(file)
    try:
        while loader.check_data():
            yield loader.get_data()
    finally:
        loader.dispose()


def parse_orchestrator_config(config_file):
    resolved_tasks = defaultdict(list)
    job_cache = {}

    with open(config_file, "r") as file:
        for chunk in load_yaml_chunks(file):
            config_data = expand_env_vars(chunk)
            if "jobs" in config_data:
                job_map = {
                    job["name"]: job
                    for job in config_data["jobs"]
                    if job.get("enabled", False)
                }
                for job in job_map.values():
                    resolve_tasks(job, job_cache, job_map, resolved_tasks)

    return {k: v for k, v in resolved_tasks.items() if v}


# if __name__ == "__main__":
#     config_file = "orchestrator.yaml"
#     resolved_tasks = parse_orchestrator_config(config_file)
#     print(resolved_tasks)
