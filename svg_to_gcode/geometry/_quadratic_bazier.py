from svg_to_gcode.geometry import Vector
from svg_to_gcode.geometry import Curve


class QuadraticBezier(Curve):
    """The QuadraticBezier class inherits from the abstract Curve class and describes a quadratic bezier."""

    __slots__ = 'control'

    def __init__(self, start: Vector, end: Vector, control: Vector, stroke_width="0", stroke="", style=""):

        self.start = start
        self.end = end
        self.control = control
        self.stroke_width = stroke_width
        self.stroke = stroke
        self.style = style

        self.sanity_check()

    def __repr__(self):
        return f"QuadraticBezier(start: {self.start}, end: {self.end}, control: {self.control}, stroke_width:{self.stroke_width}, stroke: {self.stroke}, style: {self.style})"

    def point(self, t):
        return self.control + ((1 - t)**2) * (self.start - self.control) + (t**2) * (self.end - self.control)

    def derivative(self, t):
        return 2 * (1 - t) * (self.control - self.start) + 2 * t * (self.end - self.control)

    def sanity_check(self):
        # ToDo verify if self.start == self.end forms a valid curve under the svg standard
        pass
