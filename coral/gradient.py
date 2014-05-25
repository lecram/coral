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

import bisect

class Gradient:

    def __init__(self, points):
        points.sort(key=lambda p: p[0])
        if points[0][0] > 0:
            points.insert(0, (0, points[0][1]))
        if points[-1][0] < 1:
            points.append((1, points[-1][1]))
        self.pos = [p[0] for p in points]
        self.rgb = [p[1] for p in points]

    def get(self, x):
        ib = bisect.bisect_left(self.pos, x)
        if self.pos[ib] == x:
            return self.rgb[ib]
        ia = ib - 1
        pa = self.pos[ia]
        pb = self.pos[ib]
        fa = (pb - x) / (pb - pa)
        fb = (x - pa) / (pb - pa)
        ca = self.rgb[ia]
        cb = self.rgb[ib]
        return tuple(ia * fa + ib * fb for ia, ib in zip(ca, cb))

    def get_hex(self, x):
        c = self.get(x)
        return "#" + "".join(hex(int(i * 15))[2] for i in c)

gray = Gradient([
  (0.00, (0, 0, 0)),
  (1.00, (1, 1, 1)),
])

bwr = Gradient([
  (0.00, (0, 0, 1)),
  (0.50, (1, 1, 1)),
  (1.00, (1, 0, 0)),
])

heat = Gradient([
  (0.00, (0, 0, 1)),
  (0.25, (0, 1, 1)),
  (0.50, (0, 1, 0)),
  (0.75, (1, 1, 0)),
  (1.00, (1, 0, 0)),
])

height = Gradient([
  (0.00, (0.00, 0.36, 0.18)),
  (0.25, (0.84, 0.84, 0.39)),
  (0.57, (0.63, 0.39, 0.00)),
  (1.00, (1.00, 1.00, 1.00))
])

if __name__ == "__main__":
    g = Gradient([(0, (0, 0, 0)), (0.5, (0.2, 0.3, 0.4)), (1, (1, 0.75, 0.5))])
    print(g.get(0))
    print(g.get(1))
    print(g.get(0.5))
    print(g.get(0.25))
    print(g.get(0.75))
    print(g.get_hex(0))
    print(g.get_hex(1))
