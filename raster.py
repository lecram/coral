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

import png

class PixMap:

    def __init__(self, width, height, bg=255):
        self.width = width
        self.height = height
        self.pixmap = [[bg] * width for i in range(height)]

    def splitpolygon(self, points):
        polys = []
        poly = []
        for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
            if x1 - x0 > self.width / 2:
                ym = y0 + round((y1 - y0) * x0 / (x0 + self.width - x1 + 1))
                poly.extend([(x0, y0), (0, ym)])
                polys.append(poly)
                poly = []
            elif x0 - x1 > self.width / 2:
                ym = y1 - round((y1 - y0) * x1 / (x1 + self.width - x0 + 1))
                poly.extend([(x0, y0), (self.width - 1, ym)])
                polys.append(poly)
                poly = []
            else:
                poly.append((x0, y0))
        if polys:
            polys[0] = poly + polys[0]
        else:
            polys = [poly]
        return polys

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
            if y1 - y0 > self.height / 2:
                # ToDo:
                #  -split segment in two parts, top and bottom, and handle them.
                continue
            if abs(x1 - x0) > self.width / 2:
                continue
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
                if d0:
                    while x0 < x1:
                        self.pixmap[y][x0] = color
                        x0 += 1
                else:
                    x0 = x1
                d0 = d1
                x1, d1 = heapq.heappop(marks)

    def strokepolygon(self, points, color):
        "Draw polygon perimeter using Bresenham's line algorithm."

        maxd = min(self.width, self.height) / 2
        for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
            if math.hypot(x1 - x0, y1 - y0) > maxd:
                continue
            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            sx = x0 < x1 and 1 or -1
            sy = y0 < y1 and 1 or -1
            err = dx - dy
            while True:
                self.pixmap[y0][x0] = color
                if (x0, y0) == (x1, y1):
                    break
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x0 += sx
                if (x0, y0) == (x1, y1):
                    self.pixmap[y0][x0] = color
                    break
                if e2 < dx:
                    err += dx
                    y0 += sy

    def drawpredicate(self, func, color):
        "Draw pixels for which `func(x, y)` returns True."
        for y in range(self.height):
            for x in range(self.width):
                if func(x, y):
                    self.pixmap[y][x] = color

    def save(self, fname, reverse=True, **kwargs):
        writer = png.Writer(self.width, self.height, compression=9, **kwargs)
        pm = self.pixmap
        if reverse:
            pm = pm[::-1]
        if isinstance(pm[0][0], tuple):
            pm = [sum(row, ()) for row in pm]
        with open(fname, "wb") as f:
            writer.write(f, pm)
