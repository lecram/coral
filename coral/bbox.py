# Copyright (c) 2014 Marcel Rodrigues
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import math
import functools

@functools.total_ordering
class BBox:

    """BBox() -> empty box
       BBox((x0, y0), (x1, y1)) -> bounding box with specified corners
       BBox(iterable) -> bounding box that acomodates all specified points
    """
    __slots__ = 'x0', 'y0', 'x1', 'y1'

    def __init__(self, *args):
        nargs = len(args)
        if nargs == 0:
            self.x0 = self.y0 = self.x1 = self.y1 = 0
        elif nargs == 1:
            points, = args
            length = len(points)
            xs = [None] * length
            ys = [None] * length
            for i, (x, y) in enumerate(points):
                xs[i] = x
                ys[i] = y
            self.x0 = min(xs)
            self.y0 = min(ys)
            self.x1 = max(xs)
            self.y1 = max(ys)
        elif nargs == 2:
            p0, p1 = args
            self.x0, self.y0 = p0
            self.x1, self.y1 = p1
        else:
            msg = "Wrong number of arguments to BBox(): {}.".format(nargs)
            raise Exception(msg)

    def __repr__(self):
        return "BBox(({o.x0}, {o.y0}), ({o.x1}, {o.y1}))".format(o=self)

    def __hash__(self):
        return hash((self.x0, self.y0, self.x1, self.y1))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __lt__(self, other):
        return self.area() < other.area()

    def __bool__(self):
        return bool(self.area())

    def __or__(self, other):
        if not self: return other
        if not other: return self
        x0 = min(self.x0, other.x0)
        y0 = min(self.y0, other.y0)
        x1 = max(self.x1, other.x1)
        y1 = max(self.y1, other.y1)
        return BBox((x0, y0), (x1, y1))

    def __and__(self, other):
        if not self or not other: return BBox()
        x0 = max(self.x0, other.x0)
        y0 = max(self.y0, other.y0)
        x1 = min(self.x1, other.x1)
        y1 = min(self.y1, other.y1)
        if x0 >= x1 or y0 >= y1:
            return BBox()
        else:
            return BBox((x0, y0), (x1, y1))

    def copy(self):
        """Return an exact copy of the BBox."""
        return BBox((self.x0, self.y0), (self.x1, self.y1))

    def center(self):
        """Return the center point of the BBox."""
        x = (self.x0 + self.x1) / 2
        y = (self.y0 + self.y1) / 2
        return x, y

    def width(self):
        """Return the width of the BBox."""
        return self.x1 - self.x0

    def height(self):
        """Return the height of the BBox."""
        return self.y1 - self.y0

    def area(self):
        """Return the area of the BBox."""
        return (self.x1 - self.x0) * (self.y1 - self.y0)

    def hypot(self):
        """Return the length of the diagonal of the BBox."""
        return math.hypot(self.x1 - self.x0, self.y1 - self.y0)

    def has_point(self, point):
        """Return whether a point is inside the BBox."""
        x, y = point
        return self.x0 <= x < self.x1 and self.y0 <= y < self.y1

    def has_bbox(self, other):
        """Return whether another BBox is inside the BBox."""
        p0 = other.x0, other.y0
        p1 = other.x1, other.y1
        return self.has_point(p0) and self.has_point(p1)

    def collide(self, other):
        """Return whether another BBox collides with the BBox."""
        xok = ((self.x0 <= other.x0 < self.x1) or
               (other.x0 <= self.x0 < other.x1))
        yok = ((self.y0 <= other.y0 < self.y1) or
               (other.y0 <= self.y0 < other.y1))
        return xok and yok

    def translate(self, dx, dy):
        """Return a copy of BBox translated."""
        x0 = self.x0 + dx
        y0 = self.y0 + dy
        x1 = self.x1 + dx
        y1 = self.y1 + dy
        return BBox((x0, y0), (x1, y1))

    def scale(self, factor):
        """Return a copy of BBox scaled from the center."""
        half_factor = factor / 2
        half_width  = self.width()  * half_factor
        half_height = self.height() * half_factor
        cx, cy = self.center()
        x0 = cx - half_width
        y0 = cy - half_height
        x1 = cx + half_width
        y1 = cy + half_height
        return BBox((x0, y0), (x1, y1))
