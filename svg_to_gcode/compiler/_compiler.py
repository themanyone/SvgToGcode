import typing
import warnings

from svg_to_gcode.compiler.interfaces import Interface
from svg_to_gcode.geometry import Curve, Line
from svg_to_gcode.geometry import LineSegmentChain
from svg_to_gcode import UNITS, TOLERANCES
from svg_to_gcode.compiler._hex2gray import from_hex
from svg_to_gcode.compiler._hex2gray import from_rgb

class Compiler:
    """
    The Compiler class handles the process of drawing geometric objects using interface commands and assembling
    the resulting numerical control code.
    """

    def __init__(self, interface_class: typing.Type[Interface], movement_speed, cutting_speed, pass_depth,
                 dwell_time=0, unit=None, custom_header=None, custom_footer=None):
        """

        :param interface_class: Specify which interface to use. The most common is the gcode interface.
        :param movement_speed: the speed at which to move the tool when moving. (units are determined by the printer)
        :param cutting_speed: the speed at which to move the tool when cutting. (units are determined by the printer)
        :param pass_depth: AKA, the depth your laser cuts in a pass.
        :param dwell_time: the number of ms the tool should wait before moving to another cut. Useful for pen plotters.
        :param unit: specify a unit to the machine
        :param custom_header: A list of commands to be executed before all generated commands. Default is [laser_off,]
        :param custom_footer: A list of commands to be executed after all generated commands. Default is [laser_off,]
        """
        self.interface = interface_class()
        self.movement_speed = movement_speed
        self.cutting_speed = cutting_speed
        self.speed_multiplier = 1
        self.pass_depth = abs(pass_depth)
        self.dwell_time = dwell_time
        self.laser_power = 1

        if (unit is not None) and (unit not in UNITS):
            raise ValueError(f"Unknown unit {unit}. Please specify one of the following: {UNITS}")
        
        self.unit = unit

        if custom_header is None:
            custom_header = [self.interface.laser_off()]

        if custom_footer is None:
            custom_footer = [self.interface.laser_off()]

        self.header = [self.interface.set_absolute_coordinates(),
                       self.interface.set_movement_speed(self.movement_speed)] + custom_header
        self.footer = custom_footer
        self.body = []

    def compile(self, passes=1):

        """
        Assembles the code in the header, body and footer, saving it to a file.


        :param passes: the number of passes that should be made. Every pass the machine moves_down (z-axis) by
        self.pass_depth and self.body is repeated.
        :return returns the assembled code. self.header + [self.body, -self.pass_depth] * passes + self.footer
        """

        if len(self.body) == 0:
            warnings.warn("Compile with an empty body (no curves). Is this intentional?")

        gcode = []

        gcode.extend(self.header)
        gcode.append(self.interface.set_unit(self.unit))
        for i in range(passes):
            gcode.extend(self.body)

            if i < passes - 1:  # If it isn't the last pass, turn off the laser and move down
                gcode.append(self.interface.laser_off())

                if self.pass_depth > 0:
                    gcode.append(self.interface.set_relative_coordinates())
                    gcode.append(self.interface.linear_move(z=-self.pass_depth))
                    gcode.append(self.interface.set_absolute_coordinates())

        gcode.extend(self.footer)

        gcode = filter(lambda command: len(command) > 0, gcode)

        return '\n'.join(gcode)

    def compile_to_file(self, file_name: str, passes=1):
        """
        A wrapper for the self.compile method. Assembles the code in the header, body and footer, saving it to a file.

        :param file_name: the path to save the file.
        :param passes: the number of passes that should be made. Every pass the machine moves_down (z-axis) by
        self.pass_depth and self.body is repeated.
        """

        with open(file_name, 'w') as file:
            file.write(self.compile(passes=passes))

    def append_line_chain(self, line_chain: LineSegmentChain):
        """
        Draws a LineSegmentChain by calling interface.linear_move() for each segment. The resulting code is appended to
        self.body
        """

        if line_chain.chain_size() == 0:
            warnings.warn("Attempted to parse empty LineChain")
            return []
        
        code = []
        line0 = line_chain.get(0)
        start = line0.start
        self.speed_multiplier = 1.0
        opacity = 1.0
        gray = 0.0
        # Apply speed and power multipliers based on line width and stroke (color).
        # The user sets maximum power and speed of the laser in the interface.
        # Thick lines give max power. White lines give max speed.
        # Thin, white lines give max speed, minimum power, for visual placement.
        # Thick, black lines give min speed, max power, for cutting plywood.
        if float(line0.stroke_width) > 0:
            # Thin lines reduce laser power from 0mm (off) to 1mm (max power).
            self.laser_power = float(line0.stroke_width)
            # Lines over 1mm thick do not further increase power.
            if self.laser_power > 1:
                self.laser_power = 1
        if hasattr(line0, 'opacity'):
            # Reduce cutting speed from opaque (1/10 speed) to clear (max speed).
            opacity = line0.opacity
        if hasattr(line0, 'stroke'):
            # Reduce cutting speed from black (1/10 speed) to white (max speed).
            gray = from_rgb(line0.stroke)
        if hasattr(line0, 'style'):
            # If styles are present, use those instead. Inkscape prefers this.
            if line0.style.rpartition("opacity:")[1]:
                opacity = float(line0.style.rpartition("opacity:")[2].partition(';')[0])
            if line0.style.rpartition("stroke:")[1]:
                gray = from_hex(line0.style.rpartition("stroke:")[2].partition(';')[0])
#            Gray + opacity = laser speed
#            self.speed_multiplier = 1 - opacity + 0.1
#            self.speed_multiplier = gray * 0.997824 + 0.1
            if line0.style.rpartition("stroke-width:")[1]:
                width = line0.style.rpartition("stroke-width:")[2].partition(';')[0]
                self.speed_multiplier = 1 - float(width)
        self.laser_power = opacity - round(gray * 0.997826086956047, 4)

        # Don't dwell and turn off laser if the new start is at the current position
        if self.interface.position is None or abs(self.interface.position - start) > TOLERANCES["operation"]:

            code = [self.interface.laser_off(), self.interface.set_movement_speed(self.movement_speed),
                    self.interface.linear_move(start.x, start.y, c=0), self.interface.set_movement_speed(self.cutting_speed * self.speed_multiplier),
                    self.interface.set_laser_power(self.laser_power)]

            if self.dwell_time > 0:
                code = [self.interface.dwell(self.dwell_time)] + code

        for line in line_chain:
            code.append(self.interface.linear_move(line.end.x, line.end.y))

        self.body.extend(code)

    def append_curves(self, curves: [typing.Type[Curve]]):
        """
        Draws curves by approximating them as line segments and calling self.append_line_chain(). The resulting code is
        appended to self.body
        """

        for curve in curves:
            line_chain = LineSegmentChain()

            approximation = LineSegmentChain.line_segment_approximation(curve)

            line_chain.extend(approximation)

            self.append_line_chain(line_chain)
