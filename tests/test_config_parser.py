import os
import unittest
from collections import defaultdict
from unittest.mock import mock_open, patch

from porchestrator.parser import (
    expand_env_vars,
    load_yaml_chunks,
    parse_orchestrator_config,
    resolve_tasks,
)


class TestOrchestrator(unittest.TestCase):

    def test_expand_env_vars_str(self):
        os.environ["TEST_VAR"] = "test_value"
        self.assertEqual(expand_env_vars("$TEST_VAR"), "test_value")
        del os.environ["TEST_VAR"]

    def test_expand_env_vars_dict(self):
        os.environ["TEST_VAR"] = "test_value"
        data = {"key": "$TEST_VAR"}
        self.assertEqual(expand_env_vars(data), {"key": "test_value"})
        del os.environ["TEST_VAR"]

    def test_expand_env_vars_list(self):
        os.environ["TEST_VAR"] = "test_value"
        data = ["$TEST_VAR"]
        self.assertEqual(expand_env_vars(data), ["test_value"])
        del os.environ["TEST_VAR"]

    def test_expand_env_vars_other(self):
        self.assertEqual(expand_env_vars(123), 123)

    def test_resolve_tasks(self):
        job = {
            "name": "job1",
            "needs": ["job2"],
            "run": {
                "p0": ["task1"],
                "p1": ["task2"],
                "p2": ["task3"],
            },
            "enabled": True,
        }
        dependency_job = {
            "name": "job2",
            "run": {
                "p0": ["task4"],
                "p1": ["task5"],
                "p2": ["task6"],
            },
            "enabled": True,
        }
        job_map = {"job1": job, "job2": dependency_job}
        resolved_tasks = defaultdict(list)
        job_cache = {}

        resolve_tasks(job, job_cache, job_map, resolved_tasks)

        self.assertEqual(resolved_tasks["p0"], ["task4", "task1"])
        self.assertEqual(resolved_tasks["p1"], ["task5", "task2"])
        self.assertEqual(resolved_tasks["p2"], ["task6", "task3"])

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="jobs:\n  - name: job1\n    enabled: true\n    run:\n      p0: [task1]\n",
    )
    @patch("porchestrator.parser.expand_env_vars", side_effect=lambda x: x)
    def test_parse_orchestrator_config(self, mock_expand_env_vars, mock_open):
        resolved_tasks = parse_orchestrator_config("fake_config.yaml")
        self.assertEqual(resolved_tasks, {"p0": ["task1"]})

    @patch("porchestrator.parser.yaml.SafeLoader")
    def test_load_yaml_chunks(self, mock_safe_loader):
        mock_loader_instance = mock_safe_loader.return_value
        mock_loader_instance.check_data.side_effect = [True, False]
        mock_loader_instance.get_data.return_value = {"key": "value"}

        file_content = "---\nkey: value\n"
        with patch("builtins.open", mock_open(read_data=file_content)):
            with open("fake_file.yaml", "r") as file:
                chunks = list(load_yaml_chunks(file))

        self.assertEqual(chunks, [{"key": "value"}])
        mock_loader_instance.dispose.assert_called_once()


if __name__ == "__main__":
    unittest.main()
