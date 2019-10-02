#!/usr/bin/env python

import logging
import unittest

from bardolph.controller.instruction import Instruction, OpCode
from bardolph.parser.parse import Parser

class ParserTest(unittest.TestCase):
    def setUp(self):
        logging.getLogger().addHandler(logging.NullHandler())
        self.parser = Parser()
        
    def good_input(self, input_string):
        self.assertTrue(self.parser.parse(input_string))
    
    def test_good_strings(self):
        input_strings = [ 
            '#abcde \n hue 5 \n #efghi \n ',
            '',
            'set "name with spaces"',
            'define table "Table" set table',
            'hue 5 saturation 10 set "Table"',
            'hue 5 set all',
            'get all get "Table" get group "group" get location "location"'
        ]
        for s in input_strings:    
            self.assertIsNotNone(self.parser.parse(s), s)

    def test_bad_keyword(self):
        input_string = 'on "Top" on "Bottom" on\n"Middle" Frank'
        self.assertFalse(self.parser.parse(input_string))
        self.assertIn("Unexpected input", self.parser.get_errors())

    def test_bad_number(self):
        input_string = "hue 5 saturation x"
        self.assertFalse(self.parser.parse(input_string))
        self.assertIn("Unknown parameter value", self.parser.get_errors())
        
    def test_logical_units(self):
        input_string = 'hue 0 saturation 0 brightness 0'
        expected = [
            Instruction(OpCode.SET_REG, "hue", 0), 
            Instruction(OpCode.SET_REG, "saturation", 0), 
            Instruction(OpCode.SET_REG, "brightness", 0)
        ]
        actual = self.parser.parse(input_string)
        self.assertEqual(expected, actual,
            "Unit conversion failed: {} {}".format(expected, actual))

        input_string = 'hue 360.0 saturation 100.0 brightness 100.0'
        expected = [
            Instruction(OpCode.SET_REG, "hue", 0), 
            Instruction(OpCode.SET_REG, "saturation", 65535), 
            Instruction(OpCode.SET_REG, "brightness", 65535)
        ]        
        actual = self.parser.parse(input_string)
        self.assertEqual(expected, actual,
            "Unit conversion failed: {} {}".format(expected, actual))
        
        input_string = 'hue 180.0 saturation 20 brightness 40'
        expected = [
            Instruction(OpCode.SET_REG, "hue", 32768), 
            Instruction(OpCode.SET_REG, "saturation", 13107), 
            Instruction(OpCode.SET_REG, "brightness", 26214)
        ]        
        actual = self.parser.parse(input_string)
        self.assertEqual(expected, actual,
            "Unit conversion failed: {} {}".format(expected, actual))
        
    def test_unit_switch(self):
        input_string = """hue 360 saturation 100 units raw hue 5 brightness 10
            units logical hue 90 saturation 50"""
        expected = [
            Instruction(OpCode.SET_REG, "hue", 0), 
            Instruction(OpCode.SET_REG, "saturation", 65535), 
            Instruction(OpCode.SET_REG, "hue", 5),
            Instruction(OpCode.SET_REG, "brightness", 10), 
            Instruction(OpCode.SET_REG, "hue", 16384), 
            Instruction(OpCode.SET_REG, "saturation", 32768),
        ]
        actual = self.parser.parse(input_string)
        self.assertEqual(expected, actual,
            "Unit switch failed: {} {}".format(expected, actual))
                
    def test_optimizer(self):
        input_string = 'units raw hue 5 saturation 10 hue 5 brightness 20'
        expected = [
            Instruction(OpCode.SET_REG, "hue", 5), 
            Instruction(OpCode.SET_REG, "saturation", 10), 
            Instruction(OpCode.SET_REG, "brightness", 20)
        ]
        actual = self.parser.parse(input_string)
        self.assertEqual(expected, actual,
            "Optimizer failed: {} {}".format(expected, actual))
        
if __name__ == '__main__':
    unittest.main()
