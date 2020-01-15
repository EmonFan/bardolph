#!/usr/bin/env python3

import time
import unittest

from bardolph.controller import i_controller 
from bardolph.controller.script_job import ScriptJob
from bardolph.lib.injection import provide
from bardolph.lib.job_control import JobControl
from . import test_module

class EndToEndTest(unittest.TestCase):
    def setUp(self):
        test_module.configure()
        
    def _run_script(self, script):
        jobs = JobControl()
        jobs.add_job(ScriptJob.from_string(script))
        max_waits = 10
        while jobs.has_jobs():
            time.sleep(0.01)
            max_waits -= 1
            if max_waits < 0:
                self.fail("Jobs didn't finish.")

    def _check_call_list(self, light_names, expected):
        lifx = provide(i_controller.Lifx)
        for light in lifx.get_lights():
            if light.get_label() in light_names:
                self.assertListEqual(light.call_list(), expected)
        
    def _check_all_call_lists(self, expected):
        lifx = provide(i_controller.Lifx)
        for light in lifx.get_lights():
            self.assertListEqual(light.call_list(), expected)
        
    def test_individual(self):
        script = """
            units raw
            hue 11 saturation 22 brightness 33 kelvin 2500 set "Top" 
            hue 44 saturation 55 brightness 66 set "Bottom"
        """
        self._run_script(script)
        lifx = provide(i_controller.Lifx)
        for light in lifx.get_lights():
            if light.get_label() == 'Top':
                expected = [('set_color', ([11, 22, 33, 2500], 0))]
            elif light.get_label() == 'Bottom':
                expected = [('set_color', ([44, 55, 66, 2500], 0))]
            else:
                expected = []
            self.assertListEqual(light.call_list(), expected)

    def test_power(self):
        script = 'on "Top" off "Bottom"'
        self._run_script(script)
        lifx = provide(i_controller.Lifx)
        for light in lifx.get_lights():
            if light.get_label() == "Top":
                expected = [('set_power', (65535, 0))]
            elif light.get_label() == "Bottom":
                expected = [('set_power', (0, 0))]
            else:
                expected = []
            self.assertListEqual(light.call_list(), expected)

    def test_and(self):
        script = """
            units raw hue 1 saturation 2 brightness 3 kelvin 4
            duration 5 set "Bottom" and "Top" and "Middle"
        """
        self._run_script(script)
        lifx = provide(i_controller.Lifx)
        for light in lifx.get_lights():
            if light.get_label() in ('Bottom', 'Middle', 'Top'):
                expected = [('set_color', ([1, 2, 3, 4], 5))]
            else:
                expected = []
            self.assertListEqual(light.call_list(), expected)

    def test_mixed_and(self):
        script = """
            units raw hue 10 saturation 20 brightness 30 kelvin 40
            duration 50 set "Table" and group "Pole"
        """
        self._run_script(script)
        self._check_call_list(
            ('Top', 'Middle', 'Bottom', 'Table'),
            [('set_color', ([10, 20, 30, 40], 50))])
            
    def test_set_zone(self):
        script = """
            units raw hue 10 saturation 20 brightness 30 kelvin 40 duration 50
            set "Strip" zone 5 7
        """
        self._run_script(script)
        self._check_call_list(
            ('Strip'),  
            [('set_zone_color', (5, 7, [10, 20, 30, 40], 50))])
    
    def test_define_operand(self):
        script = """
            units raw define light_name "Top"
            hue 1 saturation 2 brightness 3 kelvin 4 duration 5
            set light_name
            on light_name
        """
        self._run_script(script)
        self._check_call_list(('Top'),
            [('set_color', ([1, 2, 3, 4], 5)),
             ('set_power', (65535, 5.0))])
            
    def test_define_value(self):
        script = """
            units raw define x 500
            hue 1 saturation 2 brightness 3 kelvin 4 duration x time x
            set "Top"
        """
        self._run_script(script)
        self._check_call_list(('Top'), [('set_color', ([1, 2, 3, 4], 500))])
        
    def test_zones(self):
        script = """
            units raw
            hue 5 saturation 10 brightness 15 kelvin 20 duration 25
            set "Strip" zone 0 5
            set "Strip" zone 1
        """
        self._run_script(script)
        self._check_call_list(('Strip'), [
            ('set_zone_color', (0, 5, [5, 10, 15, 20], 25.0)),
            ('set_zone_color', (1, 1, [5, 10, 15, 20], 25.0))
        ])
        
    def test_define_zones(self):
        script = """
            units raw
            hue 50 saturation 100 brightness 150 kelvin 200 duration 250
            define z1 0 define z2 5 define light "Strip"
            set light zone z1 z2
            set light zone z2
        """
        self._run_script(script)
        self._check_call_list(('Strip'),[
            ('set_zone_color', (0, 5, [50, 100, 150, 200], 250)),
            ('set_zone_color', (5, 5, [50, 100, 150, 200], 250))
        ])

    def test_group(self):
        script = """
            units raw
            hue 100 saturation 10 brightness 1 kelvin 1000
            set group "Pole"
            on group "Furniture" 
        """
        self._run_script(script)
        self._check_call_list(('Top', 'Middle', 'Bottom'),
            [('set_color', ([100, 10, 1, 1000], 0))])
        self._check_call_list(('Table', 'Chair', 'Strip'),
            [('set_power', (65535, 0))])

    def test_location(self):
        script = """
            units raw
            hue 100 saturation 10 brightness 1 kelvin 1000
            set location "Home"
            on location "Home" 
        """
        self._run_script(script)
        self._check_all_call_lists([
            ('set_color', ([100, 10, 1, 1000], 0)),
            ('set_power', (65535, 0))])


if __name__ == '__main__':
    unittest.main()