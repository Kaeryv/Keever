import unittest
import sys
sys.path.append("./tests/units/")
from keever.runners import ScriptRunner, ModuleRunner

class ScriptRunnerBasic(unittest.TestCase):
    def test_launch(self):
        runner = ScriptRunner("simple", "tests/units/resources/simple.proto.sh", shell="bash", parallel=False, workdir=".")
        assert("test" in runner.variables and len(runner.variables) == 2)
        result = runner.run_with_dict({"test": 42})
        assert("test" in result and result["test"] == 42)

    def test_launch_module(self):
        runner = ModuleRunner("dummy_mod", "resources.dummy_mod", workdir=".")
        try:
            # This code schould produce exception
            result = runner.run_with_dict({"test": 42})
            assert(False)
        except:
            assert(len(runner.variables) == 0)
