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
P format v0

P files store geometric data for geographic entities. It always use geographical
 coordinates (longitude and latitude).

Coordinates values can have sizes 1, 2, 4 or 8.

The total number of coordinates must be less than 2 ^ 32 ~= 4 billion.


This module provides classes to write and read P data sets.

To convert a shapefile to a P file:
~~~~
sf2pf(sfpath, pfpath, getname, size=4)
~~~~

`getname` is a function that takes a shapefile record as argument and returns a
 name.
`size` can be 1, 2, 4 or 8.

To write a file from scratch:
~~~~
writer = Writer(pfpath, 4)
for name, polygons in entities:
    writer.write(name, polygons)
writer.close()              # never forget this.
~~~~

Reading a data set is straightforward:
~~~~
reader = Reader(pfpath)
polygons = reader.read(0)   # first entity.
reader.close()              # optional, just to close file handle.
~~~~

One can also get a polygon by its name:
~~~~
reader = Reader("uf.p")
polygons = reader.get("35") # entity of name "35".
reader.close()              # optional, just to close a file handle.
~~~~
"""

import struct
import math

from . import shapefile, bbox, coord

UMAX1 = (1 << 8) - 1
UMAX2 = (1 << 16) - 1
UMAX4 = (1 << 32) - 1
UMAX8 = (1 << 64) - 1

def base128(v):
    digits = []
    while v >= 128:
        digits = [v % 128] + digits
        v >>= 7
    return [v] + digits

def writevlv(f, v):
    ds = base128(v)
    for d in ds[:-1]:
        f.write(bytes((d | 0x80,)))
    f.write(bytes((ds[-1],)))

def writesvlv(f, v):
    if v < 0:
        f.write(b'\xff')
    else:
        f.write(b'\x00')
    writevlv(f, abs(v))

def writeascii(f, v):
    f.write(v.encode("ascii"))
    f.write(b'\x00')

def readvlv(f):
    v = 0
    d = ord(f.read(1))
    while d & 0x80:
        v = (v << 7) + (d & 0x7f)
        d = ord(f.read(1))
    v = (v << 7) + d
    return v

def readsvlv(f):
    s = ord(f.read(1))
    v = readvlv(f)
    if s: v = -v
    return v

def readascii(f):
    bs = b""
    b = f.read(1)
    while b != b'\x00':
        bs += b
        b = f.read(1)
    return bs.decode("ascii")

def getfmt(size):
    if size == 1:
        fmt = "BB"
        umax = UMAX1
    elif size == 2:
        fmt = ">HH"
        umax = UMAX2
    elif size == 4:
        fmt = ">II"
        umax = UMAX4
    elif size == 8:
        fmt = ">QQ"
        umax = UMAX8
    else:
        raise ValueError("invalid size: {}".format(size))
    return fmt, umax

def sf2pf(sfpath, pfpath, getname, size=4):
    sf = shapefile.Reader(sfpath)
    pf = Writer(pfpath, size)
    for sr in sf.shapeRecords():
        name = getname(sr.record)
        points = sr.shape.points
        offsets = list(sr.shape.parts) + [len(points)]
        parts = [points[a:b] for a, b in zip(offsets[:-1], offsets[1:])]
        pf.write(name, parts)
    return pf.close()

class Writer:

    def __init__(self, path, size=4):
        self.path = path
        self.size = size
        self.names = []
        self.partlens = []
        self.bboxes = []
        self.errs = []
        self.buffers = []
        self.fmt, self.umax = getfmt(size)

    def write(self, name, polygons):
        # Do not repeat first point at the end.
        parts = [[None] * len(polygon) for polygon in polygons]
        for i, polygon in enumerate(polygons):
            for j, (lon, lat) in enumerate(polygon):
                while lon < -180:
                    lon += 360
                while lon > 180:
                    lon -= 360
                while lat < -90:
                    lat += 180
                while lat > 90:
                    lat += 180
                parts[i][j] = (lon, lat)
        nparts = len(parts)
        for i in range(nparts):
            part = parts[i]
            if part[0] == part[-1]:
                part = part[:-1]
                parts[i] = part
        self.names.append(name)
        bb = None
        partlen = []
        for part in parts:
            if bb is None:
                bb = bbox.BBox(part)
            else:
                bb |= bbox.BBox(part)
            partlen.append(len(part))
        self.partlens.append(partlen)
        x0 = math.floor((bb.x0 + 180) * UMAX2 / 360)
        x1 = math.ceil((bb.x1 + 180) * UMAX2 / 360)
        y0 = math.floor((bb.y0 + 90) * UMAX2 / 180)
        y1 = math.ceil((bb.y1 + 90) * UMAX2 / 180)
        if any(not 0 <= v <= UMAX2 for v in (x0, x1, y0, y1)):
            print(bb)
            print((x0, x1, y0, y1))
        self.bboxes.append((x0, x1, y0, y1))
        x0 = x0 * 360 / UMAX2 - 180
        x1 = x1 * 360 / UMAX2 - 180
        y0 = y0 * 180 / UMAX2 - 90
        y1 = y1 * 180 / UMAX2 - 90
        for part in parts:
            for point in part:
                lon1, lat1 = point
                ulon = round((lon1 - x0) * self.umax / (x1 - x0))
                ulat = round((lat1 - y0) * self.umax / (y1 - y0))
                data = struct.pack(self.fmt, ulon, ulat)
                lon2 = x0 + ulon * (x1 - x0) / self.umax
                lat2 = y0 + ulat * (y1 - y0) / self.umax
                err = coord.haversine(lon1, lat1, lon2, lat2)
                self.errs.append(err)
                self.buffers.append(data)

    def close(self):
        with open(self.path, "wb") as pf:
            # Header
            pf.write(b"PF\x00")
            pf.write(struct.pack("B", self.size))
            nrows = sum(sum(partlen) for partlen in self.partlens)
            writevlv(pf, nrows)
            # Index
            nentities = len(self.names)
            writevlv(pf, nentities)
            for idx in range(nentities):
                writeascii(pf, self.names[idx])
                partlen = self.partlens[idx]
                nparts = len(partlen)
                writevlv(pf, nparts)
                x0, x1, y0, y1 = self.bboxes[idx]
                for v in x0, x1, y0, y1:
                    pf.write(struct.pack(">H", v))
                for length in partlen:
                    writevlv(pf, length)
            # Grid
            for buf in self.buffers:
                pf.write(buf)
        return tuple(self.errs)

class Reader:

    def __init__(self, path):
        self.pf = open(path, "rb")
        assert self.pf.seekable()
        self._header()

    def __len__(self):
        return len(self.names)

    def _header(self):
        pf = self.pf
        sig = pf.read(2)
        assert sig == b'PF'
        ver = pf.read(1)
        assert ver == b'\x00'
        size = ord(pf.read(1))
        assert size in (1, 2, 4, 8)
        nrows = readvlv(pf)
        nentities = readvlv(pf)
        names = [None] * nentities
        bboxes = [None] * nentities
        partlens = [None] * nentities
        for i in range(nentities):
            name = readascii(pf)
            names[i] = name
            nparts = readvlv(pf)
            x0, = struct.unpack(">H", pf.read(2))
            x1, = struct.unpack(">H", pf.read(2))
            y0, = struct.unpack(">H", pf.read(2))
            y1, = struct.unpack(">H", pf.read(2))
            x0 = x0 * 360 / UMAX2 - 180
            x1 = x1 * 360 / UMAX2 - 180
            y0 = y0 * 180 / UMAX2 - 90
            y1 = y1 * 180 / UMAX2 - 90
            bboxes[i] = (x0, x1, y0, y1)
            partlen = [None] * nparts
            for j in range(nparts):
                length = readvlv(pf)
                partlen[j] = length
            partlens[i] = partlen
        self.datapos = pf.tell()
        self.size = size
        self.bboxes = bboxes
        self.names = names
        self.partlens = partlens
        self.fmt, self.umax = getfmt(size)

    def read(self, idx):
        pf = self.pf
        offset = self.datapos
        x0, x1, y0, y1 = self.bboxes[idx]
        for partlen in self.partlens[:idx]:
            offset += sum(partlen) * self.size * 2
        pf.seek(offset)
        parts = []
        for nrows in self.partlens[idx]:
            points = [None] * nrows
            for i in range(nrows):
                ulon, ulat = struct.unpack(self.fmt, pf.read(self.size * 2))
                lon = x0 + ulon * (x1 - x0) / self.umax
                lat = y0 + ulat * (y1 - y0) / self.umax
                points[i] = (lon, lat)
            parts.append(points)
        return parts

    def get(self, name):
        return self.read(self.names.index(name))

    def close(self):
        self.pf.close()

if __name__ == "__main__":
    shppath = "/home/marcel/Downloads/ne_110m_land"
    pfpath = "land.p"
    getname = lambda record: "_".join(map(str, record))
    errs = shp2pf(shppath, pfpath, getname, 2)
    from . import stats
    print(stats.avg(errs))
    print(stats.std_dev(errs))
    print(stats.min(errs))
    print(stats.max(errs))
