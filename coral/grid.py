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

import struct

SIZE_FORMAT = {1: 'B', 2: 'H', 4: 'I', 8: 'Q'}
SIZE_SPAN   = {1: 0x100, 2: 0x10000, 4: 0x100000000, 8: 0x10000000000000000}

class IVar:

    def __init__(self, name, minv, maxv, nullable=False):
        assert maxv > minv
        self.name = name
        self.minv = minv
        self.maxv = maxv
        delta = maxv - minv
        if delta < SIZE_SPAN[1] - nullable:
            self.size = 1
        elif delta < SIZE_SPAN[2] - nullable:
            self.size = 2
        elif delta < SIZE_SPAN[4] - nullable:
            self.size = 4
        elif delta < SIZE_SPAN[8] - nullable:
            self.size = 8
        else:
            raise ValueError
        self.span = SIZE_SPAN[self.size]
        if nullable:
            self.span -= 1
        self.nullable = nullable

    def __repr__(self):
        return "IVar({0.minv}, {0.maxv}, {0.nullable})".format(self)

    def __str__(self):
        if self.nullable:
            return "integer {0.name} in [{0.minv}; {0.maxv}] or null".format(self)
        else:
            return "integer {0.name} in [{0.minv}; {0.maxv}]".format(self)

    def index(self, value):
        if value is None:
            assert self.nullable
            return self.span + 1
        assert self.minv <= value <= self.maxv
        return value - self.minv

    def value(self, index):
        if index == self.span + 1:
            assert self.nullable
            return None
        assert 0 <= index <= self.span
        return self.minv + index

    def encode(self, value):
        return struct.pack(self.fmt, self.index(value))

    def decode(self, data):
        return self.value(struct.unpack(self.fmt, data)[0])

class FVar:

    def __init__(self, name, minv, maxv, size, nullable=False):
        assert maxv > minv
        assert size in (1, 2, 4, 8) # (B, H, I, Q)
        self.name = name
        self.fmt = '>' + SIZE_FORMAT[size]
        self.minv = minv
        self.maxv = maxv
        self.size = size
        self.delta = maxv - minv
        self.span = SIZE_SPAN[size]
        if nullable:
            self.span -= 1
        self.nullable = nullable

    def __repr__(self):
        return "FVar({0.minv}, {0.maxv}, {0.size}, {0.nullable})".format(self)

    def __str__(self):
        if self.nullable:
            return "real {0.name} in [{0.minv}; {0.maxv}] or null".format(self)
        else:
            return "real {0.name} in [{0.minv}; {0.maxv}]".format(self)

    def index(self, value):
        if value is None:
            assert self.nullable
            return self.span + 1
        assert self.minv <= value <= self.maxv
        return min(round((value - self.minv) * self.span / self.delta), self.span)

    def value(self, index):
        if index == self.span + 1:
            assert self.nullable
            return None
        assert 0 <= index <= self.span
        return self.minv + index * self.delta / self.span

    def encode(self, value):
        return struct.pack(self.fmt, self.index(value))

    def decode(self, data):
        return self.value(struct.unpack(self.fmt, data)[0])

class SVar:

    def __init__(self, name, size, nullable=False):
        self.name = name
        self.size = size
        self.nullable = nullable

    def __repr__(self):
        return "SVar({0.size}, {0.nullable})".format(self)

    def __str__(self):
        if self.nullable:
            return "string {0.name} of {0.size} bytes or null".format(self)
        else:
            return "string {0.name} of {0.size} bytes".format(self)

    def encode(self, value):
        if value is None:
            assert self.nullable
            return b'\xff' * self.size
        data = value.encode("utf8")
        assert len(data) <= self.size
        return data.ljust(self.size, b'\x00')

    def decode(self, data):
        if data == b'\xff' * self.size:
            assert self.nullable
            return None
        return data.decode("utf8").rstrip('\x00')

class GRow:

    def __init__(self, *fields):
        self.fields = fields
        self.size = sum(f.size for f in fields)

    def __len__(self):
        return len(self.fields)

    def encode(self, *values):
        data = b''.join(f.encode(v) for (f, v) in zip(self.fields, values))
        assert len(data) == self.size
        return data

    def decode(self, data):
        values = []
        offset = 0
        for f in self.fields:
            d = data[offset:offset+f.size]
            values.append(f.decode(d))
            offset += f.size
        return tuple(values)


if __name__ == "__main__":
    name  = SVar("name", 32)
    angle = FVar("angle", 0, 359, 8)
    coeff = FVar("coeff", 0, 1, 8)
    perct = FVar("perct", 0, 100, 8)
    row = GRow(name, angle, coeff, perct)
    r = ('São Gonçalo', 300, 0.5 ** 0.5, 99)
    e = row.encode(*r)
    d = row.decode(e)
    print(r, e, d)
    print(r == d)
