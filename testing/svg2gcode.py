#!/usr/bin/python
# svg_to_gcode.py
# ref. https://pypi.org/project/svg-to-gcode/
from svg_to_gcode.svg_parser import parse_file
from svg_to_gcode.compiler import Compiler, interfaces
from svg_to_gcode.formulas import linear_map
import sys

if len(sys.argv) < 2:
    exit(f"usage: {sys.argv[0]} input.svg")

class CustomInterface(interfaces.Gcode):
    def __init__(self):
        super().__init__()
        self.power = 1

    # Override the laser_off method to just say s0.
    def laser_off(self):
        return "M4 S0;" # turn off the laser

    # Override the set_laser_power method
    def set_laser_power(self, power):
        if power < 0 or power > 1:
            raise ValueError(f"{power} is out of bounds. Laser power must be given between 0 and 1. "
                             f"The interface will scale it correctly.")

        return f"S{linear_map(0, 1000, power)};"  # Turn on the fan + change laser power

# Instantiate a compiler, specifying the custom interface and the speed at which the tool should move.
gcode_compiler = Compiler(CustomInterface, movement_speed=10000, cutting_speed=1000, pass_depth=5, custom_header=["G21;"], custom_footer=["G0 X0 Y0;","S0;\n"])

curves = parse_file(sys.argv[1]) # Parse an svg file into geometric curves
print(curves)
gcode_compiler.append_curves(curves)
gcode_compiler.compile_to_file(sys.argv[1]+".gcode")
print("\nwrote", sys.argv[1]+".gcode")
