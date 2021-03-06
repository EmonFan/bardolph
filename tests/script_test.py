#!/usr/bin/env python3

import unittest

from bardolph.controller import i_controller
from bardolph.lib.injection import provide
from tests.script_runner import ScriptRunner
from tests import test_module

class ScriptTest(unittest.TestCase):
    def setUp(self):
        test_module.configure()
        self._runner = ScriptRunner(self)

    def test_script(self):
        script = """
            repeat while {brightness < 50.0} begin
                brightness {brightness + 5}
                set all
            end
        """
        self._runner.run_script(script)
        lifx = provide(i_controller.Lifx)
        for light in lifx.get_lights():
            print(light.get_label(), light.call_list())

if __name__ == '__main__':
    unittest.main()
