#!/usr/bin/env python3

import unittest

from bardolph.controller import i_controller
from bardolph.controller.units import UnitMode
from bardolph.lib.injection import provide
from bardolph.vm.instruction import Instruction
from bardolph.vm.machine import Machine
from bardolph.vm.vm_codes import OpCode, Operand, Register

from . import test_module

class MachineTest(unittest.TestCase):
    def setUp(self):
        test_module.configure()

        self._group0 = 'Group 0'
        self._group1 = 'Group 1'

        self._location0 = 'Location 0'
        self._location1 = 'Location 1'

        self._colors = [
            [4, 8, 12, 16], [24, 28, 32, 36], [44, 48, 52, 56], [64, 68, 72, 76]
        ]
        self._names = [
            "Test g1 l1", "Test g1 l2", "Test g2 l1", "Test g2 l2"
        ]

        lifx = provide(i_controller.Lifx)
        lifx.init_from([
            (self._names[0], self._group0, self._location0, self._colors[0]),
            (self._names[1], self._group0, self._location1, self._colors[1]),
            (self._names[2], self._group1, self._location0, self._colors[2]),
            (self._names[3], self._group1, self._location1, self._colors[3])
        ])
        light_set = provide(i_controller.LightSet)
        light_set.discover()

    @classmethod
    def code_for_get(cls, name, operand):
        return [
            Instruction(OpCode.MOVEQ, name, Register.NAME),
            Instruction(OpCode.MOVEQ, operand, Register.OPERAND),
            Instruction(OpCode.GET_COLOR)
        ]

    @classmethod
    def code_for_set(cls, name, operand, params):
        return [
            Instruction(OpCode.MOVEQ, UnitMode.RAW, Register.UNIT_MODE),
            Instruction(OpCode.MOVEQ, params[0], Register.HUE),
            Instruction(OpCode.MOVEQ, params[1], Register.SATURATION),
            Instruction(OpCode.MOVEQ, params[2], Register.BRIGHTNESS),
            Instruction(OpCode.MOVEQ, params[3], Register.KELVIN),
            Instruction(OpCode.MOVEQ, name, Register.NAME),
            Instruction(OpCode.MOVEQ, operand, Register.OPERAND),
            Instruction(OpCode.COLOR)
        ]

    def test_get_color(self):
        program = MachineTest.code_for_get(self._names[0], Operand.LIGHT)
        machine = Machine()
        machine.run(program)
        self.assertTrue(machine.color_from_reg(), self._colors[0])

    def test_set_single_color(self):
        color = [1, 2, 3, 4]
        name = self._names[0]

        program = MachineTest.code_for_set(name, Operand.LIGHT, color)
        machine = Machine()
        machine.run(program)
        self.assertListEqual(machine.color_from_reg(), color)
        light_set = provide(i_controller.LightSet)
        light = light_set.get_light(name)._impl
        self.assertTrue(light.was_set(color))

if __name__ == '__main__':
    unittest.main()
