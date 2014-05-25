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
RangeGrid format v1

RangeGrid files store data rows of fixed size. Each column has a name and a 
 format specification based on data type (integer, real or string) and size.

Numeric values can have sizes 1, 2, 4 or 8. Strings can have any size.

The number of columns must be less than 256. The total number of rows must be
less than 2 ^ 32 ~= 4 billion.

Each RangeGrid data set (table) is stored on a pair of files. The RG file
 contains the data of all entities and the MD file contains an index of
 entities, with their ID and segments length (number of rows).

This module provides classes to write and read RangeGrid data sets.

To write a data set one first must specify the row format:
~~~~
grow = GRow(FVar("lon", -180, 180, 8), FVar("lat", -90, 90, 8))
writer = Writer("brazil", grow)
~~~~

Then, one can write entities one by one, given their rows:
~~~~
for uf in ufs:
    writer.write(uf.points)
~~~~

It's recommended to give meaninful IDs to each entity:

~~~~
for uf in ufs:
    writer.write(uf.points, uf.id)
~~~~

Once all the data has been written, one **must** close the writer in order to
 properly save the data to disk:
~~~~
writer.close() # writes two files: "brazil.rg" and "brazil.md".
~~~~

Reading a data set is straightforward:
~~~~
reader = Reader("brazil")
for uf in ufs:
    uf.points = reader.read(uf.id)
reader.close() # optional, just to close a file handle.
~~~~

Note that the method Reader.read() takes an ID optionally. If one doesn't
 specify an ID, it will read the next entity on the stream, in the same order
 that they appear in the MD file. Also, entities can be read in random order
 if the ID is supplied.

"""

# We need some constants from the io module to use as 2nd arg to IOBase.seek():
#   s.seek(offset, io.SEEK_SET) seeks from the start of the stream (default)
#   s.seek(offset, io.SEEK_CUR) seeks from current position
#   s.seek(offset, io.SEEK_END) seeks from the end of the stream
import io
import struct

from .grid import IVar, FVar, SVar, GRow

INTEGER, REAL, STRING = range(3)

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

def _writeindex(path, index):
    with open(path, "w") as md:
        n = len(index)
        md.write("{}\n".format(n))
        for eid, elens in index:
            md.write("{} {}\n".format(eid, len(elens)))
            md.write(" ".join(str(length) for length in elens) + '\n')

def _readindex(path):
    index = []
    with open(path, "r") as md:
        n = int(md.readline())
        for i in range(n):
            eid, ensegs = md.readline().split(" ")
            ensegs = int(ensegs)
            elens = [int(s) for s in md.readline().split(" ")]
            index.append((eid, elens))
    return index

class Writer:

    def __init__(self, path, row):
        self.path = path
        self.rg = open(self.path + ".rg", "wb")
        assert self.rg.seekable()
        self.row = row
        self._header()
        self.index = []

    def _header(self):
        rg = self.rg
        ncols = len(self.row)
        assert ncols < 256
        rg.write(b'RG\x01')
        rg.write(bytes((ncols,)))
        self.nrowspos = rg.tell()
        # Skip nrows for now; see close() method.
        rg.seek(4, io.SEEK_CUR)
        for field in self.row.fields:
            rg.write(field.name.encode("ascii"))
            rg.write(b'\x00')
            if isinstance(field, IVar):
                rg.write(b'\x00')
            elif isinstance(field, FVar):
                rg.write(b'\x01')
            elif isinstance(field, SVar):
                rg.write(b'\x02')
            if field.nullable:
                rg.write(b'\x01')
            else:
                rg.write(b'\x00')
            writevlv(rg, field.size)
            if isinstance(field, (IVar, FVar)):
                writesvlv(rg, field.minv)
                writesvlv(rg, field.maxv)

    def write(self, segs, id_=None):
        rg = self.rg
        if id_ is None:
            id_ = len(self.index)
        lens = []
        for rows in segs:
            length = 0
            for r in rows:
                data = self.row.encode(*r)
                rg.write(data)
                length += 1
            lens.append(length)
        self.index.append((id_, lens))

    def close(self):
        rg = self.rg
        nrows = sum(sum(e[1]) for e in self.index)
        data = struct.pack("I", nrows)
        rg.seek(self.nrowspos)
        rg.write(data)
        rg.close()
        _writeindex(self.path + ".md", self.index)

class Reader:

    def __init__(self, path):
        self.path = path
        self.rg = open(self.path + ".rg", "rb")
        assert self.rg.seekable()
        self.index = _readindex(self.path + ".md")
        self._header()
        self.idx = 0

    def _header(self):
        rg = self.rg
        sig = rg.read(2)
        assert sig == b'RG'
        ver = rg.read(1)
        assert ver == b'\x01'
        ncols = ord(rg.read(1))
        nrows, = struct.unpack("I", rg.read(4))
        fields = [None] * ncols
        for i in range(ncols):
            bs = b''
            b = rg.read(1)
            while b != b'\x00':
                bs += b
                b = rg.read(1)
            name = bs.decode("ascii")
            tp = ord(rg.read(1))
            if tp == INTEGER:
                nullable = bool(ord(rg.read(1)))
                size = readvlv(rg)
                minv = readsvlv(rg)
                maxv = readsvlv(rg)
                fields[i] = IVar(name, minv, maxv, nullable)
            elif tp == REAL:
                nullable = bool(ord(rg.read(1)))
                size = readvlv(rg)
                minv = readsvlv(rg)
                maxv = readsvlv(rg)
                fields[i] = FVar(name, minv, maxv, size, nullable)
            elif tp == STRING:
                nullable = bool(ord(rg.read(1)))
                size = readvlv(rg)
                fields[i] = SVar(name, size, nullable=nullable)
            else:
                raise TypeError
        self.row = GRow(*fields)
        self.nt = collections.namedtuple("Row", (field.name for field in fields))
        self.datapos = rg.tell()

    def read(self, id_=None):
        rg = self.rg
        if id_ is not None:
            idx, offset = 0, 0
            for eid, elens in self.index:
                if eid == str(id_):
                    break
                idx += 1
                offset += self.row.size * sum(elens)
            else:
                raise KeyError("id not found: {}".format(id_))
            self.idx = idx
            rg.seek(self.datapos + offset)
        segs = []
        for nrows in self.index[self.idx][1]:
            rows = [self.nt(*self.row.decode(rg.read(self.row.size))) for i in range(nrows)]
            segs.append(rows)
        self.idx += 1
        return segs

    def close(self):
        self.rg.close()

if __name__ == "__main__":
    row = GRow(FVar("lon", -180, 180, 1))
    rows1 = [(-180,), (-100.5,), (0,), (40.25,), (179,)]
    path = "foo"
    w = Writer(path, row)
    w.write(rows1)
    w.close()
    r = Reader(path)
    rows2 = r.read()
    print(rows1)
    print(rows2)
