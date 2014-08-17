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
import inspect
import subprocess
import tempfile
from functools import reduce

from . import bbox, tqdm

# ToDo:
#   - generalize state dict

PSDEFAULTS = dict(
  color = (0, 0, 0),
  gray = 0,
  width = 1,
  dash = ([], 0),
)

COMMONDEF = """
/bd {bind def} bind def
/m {moveto} bd
/rm {rmoveto} bd
/l {lineto} bd
/rl {rlineto} bd
/w {setlinewidth} bd
/v {setgray} bd
/rgb {setrgbcolor} bd
/gs {gsave} bd
/gr {grestore} bd
/s {stroke} bd
/f {fill} bd
/np {newpath} bd
/cp {closepath} bd
"""

def read_defs(path):
    with open(path, "r") as f:
        # The ordering of the keys is important, hence the additional list.
        keys = []
        defs = {}
        src = ""
        for line in f:
            if line.rstrip():
                src += line
            else:
                key = src[1:src.index(' ')]
                keys.append(key)
                defs[key] = src
                src = ""
    return keys, defs

base = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
KEYS, DEFS = read_defs(os.path.join(base, "defs.ps"))
DEPS = {k: set(["sz"]) for k in "sc st str sr sbr sb sbl sl stl".split()}

class Canvas:

    def __init__(self, bgcolor=None):
        self.bgcolor = bgcolor
        self.lines = []
        self.bbox = bbox.BBox()
        self.state = PSDEFAULTS.copy()
        self.deps = set()

    def copy(self):
        canvas = Canvas(self.bgcolor)
        canvas.lines = self.lines[:]
        canvas.bbox = self.bbox.copy()
        canvas.state = self.state.copy()
        canvas.deps = self.deps.copy()
        return canvas

    def resetbbox(self):
        self.bbox = bbox.BBox()

    def setgray(self, v):
        if self.state['gray'] == v:
            return
        line = "{} v".format(v)
        self.lines.append(line)
        self.state['gray'] = v

    def setcolor(self, r, g, b):
        if self.state['color'] == (r, g, b):
            return
        line = "{} {} {} rgb".format(r, g, b)
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
        line = "{} w".format(w)
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
        line = "{} {} {} 0 360 arc cp".format(x, y, r)
        self.lines.append(line)
        if fill is not None:
            if stroke is not None:
                self.lines.append("gs")
            self.setink(fill)
            self.lines.append("f")
        if stroke is not None:
            if fill is not None:
                self.lines.append("gr")
            self.setink(stroke)
            self.lines.append("s")
        self.bbox |= bbox.BBox((x - r, y - r), (x + r, y + r))

    def addpolyline(self, points, stroke=None):
        points = iter(points)
        try:
            x0, y0 = x1, y1 = next(points)
        except StopIteration:
            return
        self.lines.append("np")
        line = "{} {} m".format(x0, y0)
        self.lines.append(line)
        for x, y in points:
            if   x < x0: x0 = x
            elif x > x1: x1 = x
            if   y < y0: y0 = y
            elif y > y1: y1 = y
            line = "{} {} l".format(x, y)
            self.lines.append(line)
        if stroke is not None:
            self.setink(stroke)
        self.lines.append("s")
        self.bbox |= bbox.BBox((x0, y0), (x1, y1))

    def addpolygon(self, points, fill=None, stroke=None):
        points = iter(points)
        try:
            x0, y0 = x1, y1 = next(points)
        except StopIteration:
            return
        self.lines.append("np")
        line = "{} {} m".format(x0, y1)
        self.lines.append(line)
        for x, y in points:
            if   x < x0: x0 = x
            elif x > x1: x1 = x
            if   y < y0: y0 = y
            elif y > y1: y1 = y
            line = "{} {} l".format(x, y)
            self.lines.append(line)
        self.lines.append("cp")
        if fill is not None:
            if stroke is not None:
                self.lines.append("gs")
            self.setink(fill)
            self.lines.append("f")
        if stroke is not None:
            if fill is not None:
                self.lines.append("gr")
            self.setink(stroke)
            self.lines.append("s")
        self.bbox |= bbox.BBox((x0, y0), (x1, y1))

    def addroundedpolygon(self, points, radius, fill=None, stroke=None):
        self.lines.append("np")
        (x1, y1), (x2, y2) = points[:2]
        startend = ((x1 + x2) / 2, (y1 + y2) / 2)
        poly = [startend] + points[1:] + points[:1]
        line = "{} {} m".format(*startend)
        self.lines.append(line)
        for (x1, y1), (x2, y2) in zip(poly[1:], poly[2:] + poly[:1]):
            line = "{} {} {} {} {} arcto".format(x1, y1, x2, y2, radius)
            self.lines.append(line)
        self.lines.append("cp")
        if fill is not None:
            if stroke is not None:
                self.lines.append("gs")
            self.setink(fill)
            self.lines.append("f")
        if stroke is not None:
            if fill is not None:
                self.lines.append("gr")
            self.setink(stroke)
            self.lines.append("s")
        self.bbox |= bbox.BBox(points)

    def addtext(self, pos, text, size, font="Times-Bold", anchor="l"):
        assert anchor in "c t tr r br b bl l tl".split()
        key = "s" + anchor
        x, y = pos
        fmt = "({}) {} /{} {} {} {}"
        line = fmt.format(text, size, font, x, y, key)
        self.lines.append(line)
        self.deps.add(key)
        self.deps.update(DEPS.get(key, set()))

    def addimage(self, data, width, position=None, scale=1, color=False):
        cwidth = (3 * width) if color else width
        height = len(data) // cwidth
        swidth = width * scale
        sheight = height * scale
        self.lines.append("gs")
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
        self.lines.append("gr")
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
        pre.append("")
        line = "1 setlinejoin"
        pre.append(line)
        pre.append(COMMONDEF)
        for key in KEYS:
            if key in self.deps:
                pre.append(DEFS[key])
        if size is not None:
            line = "{} {} translate".format(size / 2, size / 2)
            pre.append(line)
            scl = (size - margin) / max(bb.width(), bb.height())
            line = "{} {} scale".format(scl, scl)
            pre.append(line)
            cx, cy = bb.center()
            line = "{} {} translate".format(-cx, -cy)
            pre.append(line)
        if self.bgcolor is not None:
            fmt = "np {} {} m {} {} l {} {} l {} {} l cp"
            line = fmt.format(x0, y0, x1, y0, x1, y1, x0, y1)
            pre.append(line)
            if isinstance(self.bgcolor, tuple):
                line = "{} {} {} rgb f".format(*self.bgcolor)
            else:
                line = "{} v f".format(self.bgcolor)
            pre.append(line)
        with open(path, "w") as f:
            for line in pre + self.lines:
                f.write(line + '\n')

    def export(self, path, device='png256', background=None, *args, **kwargs):
        # useful devices: png{16,48,256,mono,gray,alpha}
        pspath = "/tmp/tempeps.ps"
        self.save(pspath, *args, **kwargs)
        cmd  = "gs -q -dNOPAUSE -dBATCH -dEPSCrop "
        cmd += "-sDEVICE={} -sOutputFile='{}' {}".format(device, path, pspath)
        ret = subprocess.call(cmd, shell=True)
        os.remove(pspath)
        if ret:
            return ret
        if background is not None:
            color = tuple(round(c*255) for c in background)
            cmd = "convert {} -background 'rgb{}' -flatten {}"
            cmd = cmd.format(path, color, path)
            ret = subprocess.call(cmd, shell=True)
        return ret

def export(pspath, output, device='png256', background=None):
    # useful devices: png{16,48,256,mono,gray,alpha}
    cmd  = "gs -q -dNOPAUSE -dBATCH -dEPSCrop "
    cmd += "-sDEVICE={} -sOutputFile={} {}".format(device, output, pspath)
    ret = subprocess.call(cmd, shell=True)
    if ret:
        return ret
    if background is not None:
        color = tuple(round(c*255) for c in background)
        cmd = "convert {} -background 'rgb{}' -flatten {}"
        cmd = cmd.format(path, color, path)
        ret = subprocess.call(cmd, shell=True)
    return ret

def animation(gifpath, frames, delay=10, *args, **kwargs):
    # frames is a list of Canvasses.
    n = len(frames)
    length = len(str(n))
    with tempfile.TemporaryDirectory() as folder:
        fmt = os.path.join(folder, "{{:0{}}}.png".format(length))
        bb = reduce(lambda a, b: a | b, (c.bbox for c in frames), bbox.BBox())
        bb = bb.scale(1.05)
        paths = []
        for i, canvas in tqdm.tqdm(enumerate(frames), total=n, desc="anim"):
            canvas.bbox = bb
            path = fmt.format(i)
            canvas.export(path, *args, **kwargs)
            paths.append(path)
        paths = " ".join(paths)
        cmd = "convert -delay {} -loop 0 {} {}".format(delay, paths, gifpath)
        status = subprocess.call(cmd, shell=True)
    return status
