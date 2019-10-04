#!/usr/bin/env python

import argparse

from ..lib import injection
from ..lib import settings

from . import config_values
from .i_controller import LightSet
from .lsc import Compiler
from . import light_module


def normalize_parameter(param, name):
    if isinstance(param, str):
        return '{}'.format(param) 
    else 
        if name == 'hue':
            logical_value = param * 360.0 / 65535.0
        elif name in ('saturation', 'brightness'):
            logical_value = param * 100.0 / 65535.0
        else:
            logical_value = param
        return param


class Snapshot:
    def start_snapshot(self): pass
    def start_light(self, light): pass
    def handle_setting(self, name, value): pass
    def handle_power(self, power): pass
    def end_light(self): pass
    def end_snapshot(self): pass
    
    def handle_color(self, color):
        self.handle_setting('hue', color[0])
        self.handle_setting('saturation', color[1])
        self.handle_setting('brightness', color[2])
        self.handle_setting('kelvin', color[3])
    
    @injection.inject(LightSet)
    def generate(self, light_set):
        self.start_snapshot()
        light_names = light_set.get_light_names()
        for name in light_names:
            light = light_set.get_light(name)
            self.start_light(light)
            self.handle_color(light.get_color())
            self.handle_power(light.get_power())
            self.end_light()
        self.end_snapshot()
        return self        


class ScriptSnapshot(Snapshot):
    """ Generate a .ls script. Ignore power on/off. """
    def __init__(self):
        self.light_name = ''
        self.power = True
        self.script = ''
    
    def start_snapshot(self):
        self.script = 'duration 1500\n'
        
    def start_light(self, light):
        self.light_name = light.get_label()
        
    def handle_setting(self, name, value):
        self.script += '{} {} '.format(name, value)
        
    def handle_power(self, power):
        self.power = power
          
    def end_light(self):
        self.script += 'set "{}"\n'.format(self.light_name)     
        fmt = 'on "{}"\n' if self.power else 'off "{}"\n'
        self.script += fmt.format(self.light_name)

    def get_text(self):
        return '{}\n'.format(self.script)
 
     
class InstructionSnapshot(Snapshot):
    """ Generate a list of lists, one for each light. """
    def __init__(self):
        self.light_name = ''
        self.snapshot = ''
        self.power = ''
    
    def start_snapshot(self):
        self.snapshot = ''
        
    def start_light(self, light):
        self.light_name = light.get_label()
    
    def handle_setting(self, name, value):
        self.snapshot += 'OpCode.set_reg, "{}", {},\n'.format(
            name, normalize_parameter(value, name))
    
    def handle_power(self, power):
        self.power = power
        
    def end_light(self):
        self.snapshot += 'OpCode.set_reg, "name", "{}",\n'.format(
            self.light_name)
        self.snapshot += 'OpCode.set_reg, "operand", Operand.light,\n'        
        self.snapshot += 'OpCode.color,\n'
        self.snapshot += 'OpCode.set_reg, "power", {},\n'.format(self.power)
        self.snapshot += 'OpCode.power,\n'.format(self.power)
        
    def get_text(self):
        return self.snapshot[:-2]
    
    
class TextSnapshot(Snapshot):
    """ Generate plain text. """
    def __init__(self):
        self.field_width = len('saturation  ')
        self.text = ''
        self.add_field('name').add_field('hue')
        self.add_field('saturation').add_field('brightness')
        self.add_field('kelvin').add_field('power')
        self.text += '\n'
        self.text += '-' * ((self.field_width - 1) * 6)
        self.text += '\n'
        
    def generate(self):
        super().generate()
        self.add_sets()
        return self
    
    def add_field(self, data):
        self.text += str(data).ljust(self.field_width)
        return self
                  
    def start_light(self, light):
        self.add_field(light.get_label())
        
    def handle_color(self, color):
        for x in color:       
            self.add_field(x)
            
    def handle_power(self, power):
        self.add_field(power)
            
    def end_light(self):
        self.text += '\n'    
        
    def get_text(self):
        return self.text
    
    @injection.inject(LightSet)
    def add_sets(self, lights):
        self.add_set('Groups', lights.get_group_names, lights.get_group)
        self.add_set(
            'Locations', lights.get_location_names, lights.get_location)
        
    def add_set(self, heading, name_fn, get_fn):
        self.text += '\n{}\n'.format(heading)
        self.text += '-' * 17
        self.text += '\n'
        for name in name_fn():
            self.text += '{}\n'.format(name)
            for light in get_fn(name):
                self.text += '   {}\n'.format(light.get_label())
                

class DictSnapshot(Snapshot):
    """ Generate a list of dictionaries, one for each light. """
    def __init__(self):
        self.snapshot = None
        self.current_dict = None
    
    def start_snapshot(self):
        self.snapshot = []
        self.current_dict = {}        
    
    def start_light(self, light):
        self.current_dict = {'name': light.get_label()}
          
    def handle_setting(self, name, value):
        self.current_dict[name] = value
    
    def end_light(self):
        self.snapshot.append(self.current_dict)
    
    def get_text(self):
        return str(self.get_list())
    
    def get_list(self):
        return self.snapshot


def do_gen(ctor):
    print(ctor().generate().get_text() + '\n')
        
        
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '-l', '--list', help='output instruction list', action='store_true')
    ap.add_argument(
        '-d', '--dict', help='output dictionary format', action='store_true')
    ap.add_argument(
        '-p', '--py', help='output Python file', action='store_true')
    ap.add_argument(
        '-s', '--script', help='output script format', action='store_true')
    ap.add_argument(
        '-t', '--text', help='output text format', action='store_true')
    args = ap.parse_args()
    do_script = args.script
    do_dict = args.dict
    do_list = args.list
    do_py = args.py
    do_text = args.text or (not (do_py or do_script or do_dict or do_list))  

    injection.configure()   
    settings.using_base(config_values.functional).and_override(
        {'single_light_discover': True}).configure()
    light_module.configure()
    
    if do_dict:
        do_gen(DictSnapshot)
    if do_list:
        do_gen(InstructionSnapshot)
    if do_script:
        do_gen(ScriptSnapshot)
    if do_text:
        do_gen(TextSnapshot)
    if do_py:
        text = InstructionSnapshot().generate().get_text()
        Compiler().generate_from(text)


if __name__ == '__main__':
    main()
