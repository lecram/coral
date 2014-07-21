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

"""
Tools for raster drawings.
"""

import math
import heapq
from array import array

class BaseCanvas:

    def scanpolygon(self, points, scans=None):
        """Create perimeter marks for scanlines, used to fill polygons.
        This can be called for multiple polygons, passing intermediate
         values as the `scans` parameter.
        """

        if scans is None:
            scans = [[] for i in range(self.height)]
        for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
            if y0 == y1:
                # horizontal segments do not trigger the scan.
                continue
            down = y0 < y1
            if not down:
                # consider all segments going downwards to align triggers.
                (x0, y0), (x1, y1) = (x1, y1), (x0, y0)
            if x0 == x1:
                while y0 < y1:
                    heapq.heappush(scans[y0], (x0, down))
                    y0 += 1
            else:
                sx = x0 < x1 and 1 or -1
                slope = abs((y1 - y0) / (x1 - x0))
                while y0 < y1:
                    heapq.heappush(scans[y0], (round(x0), down))
                    y0 += 1
                    x0 += sx / slope
        return scans

    def fillpolygons(self, scans, color):
        "Fill polygons previously scanned with `scanpolygon()`."

        for y, marks in enumerate(scans):
            heapq.heappush(marks, (self.width, False))
            x1, d1 = heapq.heappop(marks)
            x0, d0 = 0, not d1
            while x1 < self.width:
                if not d0:
                    while x0 < x1:
                        self[x0, y] = color
                        x0 += 1
                else:
                    x0 = x1
                d0 = d1
                x1, d1 = heapq.heappop(marks)

    def line(self, start, end, color):
        "Draw line using Bresenham's algorithm."

        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = x0 < x1 and 1 or -1
        sy = y0 < y1 and 1 or -1
        err = dx - dy
        while True:
            self[x0, y0] = color
            if (x0, y0) == (x1, y1):
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if (x0, y0) == (x1, y1):
                self[x0, y0] = color
                break
            if e2 < dx:
                err += dx
                y0 += sy

    def aaline(self, start, end, color):
        "Draw anti-aliased line using Xiaolin Wu's algorithm."

        ipart   = int
        fpart   = lambda x: math.modf(x)[0]
        rfpart  = lambda x: 1 - math.modf(x)[0]
        nearest = lambda x: int(x + 0.5) # This is *not* the same as round().
        x0, y0 = start
        x1, y1 = end
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            (x0, y0), (x1, y1) = (y0, x0), (y1, x1)
        if x0 > x1:
            (x0, y0), (x1, y1) = (x1, y1), (x0, y0)
        dx = x1 - x0
        dy = y1 - y0
        gradient = dy / dx

        # Line start.
        xend = nearest(x0)
        yend = y0 + gradient * (xend - x0)
        xgap = rfpart(x0 + 0.5)
        xpxl1 = xend
        ypxl1 = ipart(yend)
        alpha1 = rfpart(yend) * xgap
        alpha2 =  fpart(yend) * xgap
        if steep:
            self[ypxl1  , xpxl1] = color + (alpha1,)
            self[ypxl1+1, xpxl1] = color + (alpha2,)
        else:
            self[xpxl1, ypxl1  ] = color + (alpha1,)
            self[xpxl1, ypxl1+1] = color + (alpha2,)
        intery = yend + gradient

        # Line end.
        xend = nearest(x1)
        yend = y1 + gradient * (xend - x1)
        xgap = rfpart(x1 + 0.5)
        xpxl2 = xend
        ypxl2 = ipart(yend)
        alpha1 = rfpart(yend) * xgap
        alpha2 =  fpart(yend) * xgap
        if steep:
            self[ypxl2  , xpxl2] = color + (alpha1,)
            self[ypxl2+1, xpxl2] = color + (alpha2,)
        else:
            self[xpxl2, ypxl2  ] = color + (alpha1,)
            self[xpxl2, ypxl2+1] = color + (alpha2,)

        # Internal points.
        for x in range(xpxl1+1, xpxl2):
            alpha1 = rfpart(intery)
            alpha2 =  fpart(intery)
            if steep:
                self[ipart(intery)  , x] = color + (alpha1,)
                self[ipart(intery)+1, x] = color + (alpha2,)
            else:
                self[x, ipart(intery)  ] = color + (alpha1,)
                self[x, ipart(intery)+1] = color + (alpha2,)
            intery += gradient

    def strokepolygon(self, points, color, aa=True):
        "Draw polygon perimeter using Bresenham's line algorithm."

        line = self.aaline if aa else self.line
        for start, end in zip(points, points[1:] + points[:1]):
            line(start, end, color)

class BWCanvas(BaseCanvas):

    def __init__(self, width, height, bgcolor=0):
        self.width   = width
        self.height  = height
        self.bgcolor = bgcolor
        nw = math.ceil(width/8)
        n = nw * height
        self.data = array('B', (bgcolor for i in range(n)))

    def __getitem__(self, key):
        x, y = key
        i = y * self.width + x
        i, j = divmod(i, 8)
        mask = 1 << (7 - j)
        v = int(bool(self.data[i] & mask))
        return v

    def __setitem__(self, key, value):
        x, y = key
        i = y * self.width + x
        i, j = divmod(i, 8)
        mask = 1 << (7 - j)
        if value:
            self.data[i] |= mask
        else:
            self.data[i] &= ~mask

    def save(self, fname):
        with open(fname, "bw") as f:
            f.write(b"P4\n")
            f.write("{0.width} {0.height}\n".format(self).encode("ascii"))
            self.data.tofile(f)

class GrayCanvas(BaseCanvas):

    def __init__(self, width, height, bgcolor=255):
        self.width   = width
        self.height  = height
        self.bgcolor = bgcolor
        n = width * height
        self.data = array('B', (bgcolor for i in range(n)))

    def __getitem__(self, key):
        x, y = key
        i = y * self.width + x
        return self.data[i]

    def __setitem__(self, key, value):
        x, y = key
        i = y * self.width + x
        if isinstance(value, tuple): # (V, A)
            fg, a = value
            v = self.blend(self.data[i], fg, a)
        else: # Must be V
            v = value
        self.data[i] = v

    def blend(self, bg, fg, alpha):
        beta = 1 - alpha
        v = int(bg * beta + fg * alpha + 0.5)
        return v

    def save(self, fname):
        with open(fname, "bw") as f:
            f.write(b"P5\n")
            f.write("{0.width} {0.height}\n".format(self).encode("ascii"))
            f.write(b"255\n")
            self.data.tofile(f)

def _fill(color, n):
    for i in range(n):
        yield from color

class ColorCanvas(BaseCanvas):

    def __init__(self, width, height, bgcolor=(255, 255, 255)):
        self.width   = width
        self.height  = height
        self.bgcolor = bgcolor
        n = width * height
        self.data = array('B', _fill(bgcolor, n))

    def __getitem__(self, key):
        x, y = key
        i = 3 * (y * self.width + x)
        r, g, b = self.data[i:i+3]
        return r, g, b

    def __setitem__(self, key, value):
        x, y = key
        i = 3 * (y * self.width + x)
        if len(value) == 4: # (R, G, B, A)
            *fg, a = value
            color = self.blend(self.data[i:i+3], fg, a)
        else: # Must be (R, G, B)
            color = value
        self.data[i:i+3] = array('B', color)

    def blend(self, bg, fg, alpha):
        r0, g0, b0 = bg
        r1, g1, b1 = fg
        beta = 1 - alpha
        r = int(r0 * beta + r1 * alpha + 0.5)
        g = int(g0 * beta + g1 * alpha + 0.5)
        b = int(b0 * beta + b1 * alpha + 0.5)
        return r, g, b

    def save(self, fname):
        with open(fname, "bw") as f:
            f.write(b"P6\n")
            f.write("{0.width} {0.height}\n".format(self).encode("ascii"))
            f.write(b"255\n")
            self.data.tofile(f)
