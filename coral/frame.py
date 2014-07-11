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
 A frame stores information that specify the relation between the Earth's
geometry (geodesy) and a particular map geometry (usually in 2D). Each map has a
frame over which multiple layers of entities are drawn. There are two parameters
that define a unique frame:
* a projection;
* a bounding box on the projected (plane) space.

 The projection parameter must be fully specified, including the center of the
projection, the orientation of the projection and the Earth model used (sphere
or ellipsoid) along with its parameters.

 The bounding box is specified as two points, determining minimal an maximal
coordinates. The coordinate system for the bounding box is the projected one,
but without scale, i.e. with meters as unit.
"""

import math
import json

from . import coord, proj, bbox, tqdm

class Frame:

    __slots__ = 'projection', 'bounding'

    def __init__(self, projection, bounding):
        self.projection = projection
        self.bounding = bounding

    def save(self, path):
        if issubclass(type(self.projection), proj.EProj):
            model = {
                "type": "ellipsoid",
                "a": self.projection.a,
                "b": self.projection.b,
                "e": self.projection.e,
                "f": self.projection.f
            }
        else:
            model = {
                "type": "sphere",
                "r": self.projection.r
            }
        rlon, rlat = self.projection.lon0, self.projection.lat0
        lon, lat = math.degrees(rlon), math.degrees(rlat)
        d = {
            "projection": {
                "type": type(self.projection).__name__,
                "center": (lon, lat),
                "orientation": 0.0,
                "model": model
            },
            "bounding": {
                "x0": self.bounding.x0,
                "y0": self.bounding.y0,
                "x1": self.bounding.x1,
                "y1": self.bounding.y1
            }
        }
        with open(path, "w") as f:
            json.dump(d, f, indent=4)
            f.write("\n")

    def point(self, scale, point):
        lon, lat = point
        x, y = self.projection.geo2rect(lon, lat)
        x //= scale
        y //= scale
        return x, y

    def planify(self, scale, points, closed=True):
        points = (self.projection.geo2rect(lon, lat) for lon, lat in points)
        points = coord.simplify(points, scale, closed=closed)
        return points

    def cachenames(self, key, pff):
        lines = []
        for name in tqdm.tqdm(pff.names):
            for points in pff.get(name):
                xys = [self.projection.geo2rect(lon, lat) for lon, lat in points]
                bb = bbox.BBox(xys)
                if self.bounding.collide(bb):
                    lines.append(name + "\n")
                    break
        with open("{}.names".format(key), "w") as f:
            f.writelines(lines)
        return len(lines)

    def loadnames(self, key):
        with open("{}.names".format(key), "r") as f:
            names = []
            for line in f:
                names.append(line.rstrip())
        return names

def load(path):
    with open(path, "r") as f:
        d = json.load(f)
    b = d['bounding']
    bb = bbox.BBox((b['x0'], b['y0']), (b['x1'], b['y1']))
    p = d['projection']
    Proj = getattr(proj, p['type'])
    pt = p['type']
    c = p['center']
    m = p['model']
    mt = m['type']
    if mt == 'ellipsoid':
        e = Ellipsoid(*(m[k] for k in 'abef'))
        prj = Proj(c, e)
    else:
        r = m['r']
        prj = Proj(c, r)
    frame = Frame(prj, bb)
    return frame
