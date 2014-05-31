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

import os
import subprocess

from . import bbox

# ToDo:
#   - redefine some operators (lineto) to generate smaller files
#   - generalize state dict

PSDEFAULTS = dict(
  color = (0, 0, 0),
  gray = 0,
  width = 1,
  dash = ([], 0),
)

CESHOWDEF = """
/ceshow { % (string) fontsize fontname x y
    gsave
        moveto findfont exch scalefont setfont % s
        gsave
            dup false charpath flattenpath pathbbox % s x0 y0 x1 y1
        grestore
        3 -1 roll sub % s x0 x1 dy
        3 1 roll sub % s dy -dx
        2 div exch % s -dx/2 dy
        -2 div % s -dx/2 -dy/2
        rmoveto show
    grestore
} bind def
"""

class Canvas:

    def __init__(self):
        self.lines = []
        self.bbox = bbox.BBox()
        self.state = PSDEFAULTS.copy()
        self.CESHOW = False

    def resetbbox(self):
        self.bbox = bbox.BBox()

    def setgray(self, v):
        if self.state['gray'] == v:
            return
        line = "{} setgray".format(v)
        self.lines.append(line)
        self.state['gray'] = v

    def setcolor(self, r, g, b):
        if self.state['color'] == (r, g, b):
            return
        line = "{} {} {} setrgbcolor".format(r, g, b)
        self.lines.append(line)
        self.state['color'] = (r, g, b)

    def setink(self, ink):
        if isinstance(ink, tuple):
            self.setcolor(*ink)
        elif isinstance(ink, (int, float)):
            self.setgray(ink)
        else:
            tname = type(ink).__name__
            raise TypeError("expected int, float or 3-tuple, got {}".format(tname))

    def setwidth(self, w):
        if self.state['width'] == w:
            return
        line = "{} setlinewidth".format(w)
        self.lines.append(line)
        self.state['width'] = w

    def setdash(self, pattern, offset=0):
        if self.state['dash'] == (pattern, offset):
            return
        psarray = "[{}]".format(" ".join(map(str, pattern)))
        line = "{} {} setdash".format(psarray, offset)
        self.lines.append(line)
        self.state['dash'] = (pattern, offset)

    def addcircle(self, center, radius, fill=None, stroke=None):
        x, y = center
        r = radius
        line = "{} {} {} 0 360 arc closepath".format(x, y, r)
        self.lines.append(line)
        if fill is not None:
            if stroke is not None:
                self.lines.append("gsave")
            self.setink(fill)
            self.lines.append("fill")
        if stroke is not None:
            if fill is not None:
                self.lines.append("grestore")
            self.setink(stroke)
            self.lines.append("stroke")
        self.bbox |= bbox.BBox((x - r, y - r), (x + r, y + r))

    def addpolyline(self, points, stroke=None):
        self.lines.append("newpath")
        line = "{} {} moveto".format(*points[0])
        self.lines.append(line)
        for point in points[1:]:
            line = "{} {} lineto".format(*point)
            self.lines.append(line)
        self.setink(stroke)
        self.lines.append("stroke")
        self.bbox |= bbox.BBox(points)

    def addpolygon(self, points, fill=None, stroke=None):
        self.lines.append("newpath")
        line = "{} {} moveto".format(*points[0])
        self.lines.append(line)
        for point in points[1:]:
            line = "{} {} lineto".format(*point)
            self.lines.append(line)
        self.lines.append("closepath")
        if fill is not None:
            if stroke is not None:
                self.lines.append("gsave")
            self.setink(fill)
            self.lines.append("fill")
        if stroke is not None:
            if fill is not None:
                self.lines.append("grestore")
            self.setink(stroke)
            self.lines.append("stroke")
        self.bbox |= bbox.BBox(points)

    def addtext(self, pos, text, size, font="Times-Bold"):
        x, y = pos
        fmt = "({}) {} /{} {} {} ceshow"
        line = fmt.format(text, size, font, x, y)
        self.lines.append(line)
        self.CESHOW = True

    def addimage(self, data, width, position=None, scale=1, color=False):
        cwidth = (3 * width) if color else width
        height = len(data) // cwidth
        swidth = width * scale
        sheight = height * scale
        self.lines.append("gsave")
        if position is not None:
            self.lines.append("{} {} translate".format(*position))
        fmt = "{} {} scale"
        line = fmt.format(swidth, sheight)
        self.lines.append(line)
        fmt = "{} {} 8 [{} 0 0 {} 0 {}]"
        line = fmt.format(width, height, width, -height, height)
        self.lines.append(line)
        self.lines.append("{<")
        a, b = 0, cwidth
        for i in range(height):
            line = "".join("{:02x}".format(v) for v in data[a:b])
            self.lines.append(line)
            a = b
            b += cwidth
        self.lines.append(">}")
        if color:
            self.lines.append("false 3 colorimage")
        else:
            self.lines.append("image")
        self.lines.append("grestore")
        tx, ty = position or (0, 0)
        self.bbox |= bbox.BBox((tx, ty), (swidth + tx, sheight + ty))

    def save(self, path, size=None, margin=0):
        bb = self.bbox
        pre = []
        pre.append("%!PS-Adobe-3.0 EPSF-3.0")
        if size is None:
            x0, y0 = bb.x0 - margin, bb.y0 - margin
            x1, y1 = bb.x1 + margin, bb.y1 + margin
        else:
            x0, y0, x1, y1 = 0, 0, size, size
        line = "%%BoundingBox: {} {} {} {}".format(x0, y0, x1, y1)
        pre.append(line)
        line = "1 setlinejoin"
        pre.append(line)
        if size is not None:
            line = "{} {} translate".format(size / 2, size / 2)
            pre.append(line)
            scl = (size - margin) / max(bb.width(), bb.height())
            line = "{} {} scale".format(scl, scl)
            pre.append(line)
            cx, cy = bb.center()
            line = "{} {} translate".format(-cx, -cy)
            pre.append(line)
        if self.CESHOW:
            pre.append(CESHOWDEF)
        with open(path, "w") as f:
            for line in pre + self.lines:
                f.write(line + '\n')

    def export(self, path, device='png256', *args, **kwargs):
        # useful devices: png{16,48,256,mono,gray,alpha}
        pspath = "/tmp/tempeps.ps"
        self.save(pspath, *args, **kwargs)
        cmd  = "gs -q -dNOPAUSE -dBATCH -dEPSCrop "
        cmd += "-sDEVICE={} -sOutputFile='{}' {}".format(device, path, pspath)
        ret = subprocess.call(cmd, shell=True)
        os.remove(pspath)
        return ret

def export(pspath, output, device='png256'):
    # useful devices: png{16,48,256,mono,gray,alpha}
    cmd  = "gs -q -dNOPAUSE -dBATCH -dEPSCrop "
    cmd += "-sDEVICE={} -sOutputFile={} {}".format(device, output, pspath)
    return subprocess.call(cmd, shell=True)
