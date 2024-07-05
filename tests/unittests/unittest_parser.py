import os
import tempfile
import unittest

from orchestrator.parser import (
    parse_orchestrator_config,  # Replace 'your_module' with the actual module name
)


class TestOrchestratorConfigParser(unittest.TestCase):

    def create_temp_yaml(self, content):
        temp = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.yaml')
        temp.write(content)
        temp.close()
        return temp.name

    def tearDown(self):
        # Clean up any temporary files
        for attr in dir(self):
            if attr.startswith('temp_file'):
                os.unlink(getattr(self, attr))

    def test_empty_config(self):
        self.temp_file1 = self.create_temp_yaml('')
        result = parse_orchestrator_config(self.temp_file1)
        self.assertEqual(result, {})

    def test_basic_config(self):
        yaml_content = """
        jobs:
          - name: job1
            enabled: true
            run:
              p0: [task1, task2]
              p1: [task3]
        """
        self.temp_file2 = self.create_temp_yaml(yaml_content)
        result = parse_orchestrator_config(self.temp_file2)
        expected = {'p0': ['task1', 'task2'], 'p1': ['task3']}
        self.assertEqual(result, expected)

    def test_disabled_job(self):
        yaml_content = """
        jobs:
          - name: job1
            enabled: false
            run:
              p0: [task1]
        """
        self.temp_file3 = self.create_temp_yaml(yaml_content)
        result = parse_orchestrator_config(self.temp_file3)
        self.assertEqual(result, {})

    def test_dependencies(self):
        yaml_content = """
        jobs:
          - name: job1
            enabled: true
            run:
              p0: [task1]
          - name: job2
            enabled: true
            needs: [job1]
            run:
              p1: [task2]
        """
        self.temp_file4 = self.create_temp_yaml(yaml_content)
        result = parse_orchestrator_config(self.temp_file4)
        expected = {'p0': ['task1'], 'p1': ['task2']}
        self.assertEqual(result, expected)

    def test_circular_dependencies(self):
        yaml_content = """
        jobs:
          - name: job1
            enabled: true
            needs: [job2]
            run:
              p0: [task1]
          - name: job2
            enabled: true
            needs: [job1]
            run:
              p1: [task2]
        """
        self.temp_file5 = self.create_temp_yaml(yaml_content)
        result = parse_orchestrator_config(self.temp_file5)
        expected = {'p0': ['task1'], 'p1': ['task2']}
        self.assertEqual(result, expected)

    def test_env_var_expansion(self):
        os.environ['TEST_VAR'] = 'expanded'
        yaml_content = """
        jobs:
          - name: job1
            enabled: true
            run:
              p0: ['$TEST_VAR']
        """
        self.temp_file6 = self.create_temp_yaml(yaml_content)
        result = parse_orchestrator_config(self.temp_file6)
        expected = {'p0': ['expanded']}
        self.assertEqual(result, expected)

    def test_multiple_priorities(self):
        yaml_content = """
        jobs:
          - name: job1
            enabled: true
            run:
              p0: [task1]
              p1: [task2]
              p2: [task3]
        """
        self.temp_file7 = self.create_temp_yaml(yaml_content)
        result = parse_orchestrator_config(self.temp_file7)
        expected = {'p0': ['task1'], 'p1': ['task2'], 'p2': ['task3']}
        self.assertEqual(result, expected)

    def test_large_config(self):
        yaml_content = "jobs:\n" + "\n".join([f"""
  - name: job{i}
    enabled: true
    needs: [job{i-1}]
    run:
      p0: [task{i}]""" for i in range(1, 1001)])
        self.temp_file8 = self.create_temp_yaml(yaml_content)
        result = parse_orchestrator_config(self.temp_file8)
        expected = {'p0': [f'task{i}' for i in range(1, 1001)]}
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()