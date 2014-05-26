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

import codecs
import collections

def join(t1, t2, pivots=None, keys=None):
    keys1 = t1[0]._fields
    keys2 = t2[0]._fields
    if pivots is None:
        pivots = list(set(keys1) & set(keys2))
    if keys is None:
        keys = list(set(keys1) | set(keys2))
    Row = collections.namedtuple("Row", keys)
    table = []
    for r1 in t1:
        id1 = [getattr(r1, key, "") for key in pivots]
        d = r1._asdict()
        for r2 in t2:
            id2 = [getattr(r2, key, "") for key in pivots]
            if id1 == id2:
                d.update(r2._asdict())
                break
        table.append(Row(*(d.get(key, "") for key in keys)))
    return table

def getone(table, key, query):
    for row in table:
        if row._asdict()[key] == query:
            return row

def getall(table, key, query):
    for row in table:
        if row._asdict()[key] == query:
            yield row

def indexby(table, key):
    indexed = {}
    keys = [k for k in table[0]._fields if k != key]
    Row = collections.namedtuple("Row", keys)
    for row in table:
        d = row._asdict()
        newrow = Row(*(d[k] for k in keys))
        indexed[d[key]] = newrow
    return indexed

def addkey(table, key, func):
    newkeys = table[0]._fields + (key,)
    Row = collections.namedtuple("Row", newkeys)
    for row in table:
        d = row._asdict()
        d[key] = func(row)
        newrow = Row(*(d[key] for key in newkeys))
        yield newrow

def delkeys(table, keys_to_del):
    newkeys = tuple(filter(lambda i: i not in keys_to_del, table[0]._fields))
    Row = collections.namedtuple("Row", newkeys)
    for row in table:
        d = row._asdict()
        newrow = Row(*(d[key] for key in newkeys))
        yield newrow

def readfile(path, keys=None, sep=',', comm='#'):
    table = []
    with codecs.open(path, "r", "utf8") as f:
        line = ""
        while not line:
            line = f.readline().split(comm)[0].strip()
        fkeys = line.split(sep)
        if keys is None:
            keys = fkeys
        indexes = [i for i in range(len(fkeys)) if fkeys[i] in keys]
        Row = collections.namedtuple("Row", keys)
        for line in f:
            line = line.split(comm)[0].strip()
            if not line:
                continue
            fvalues = line.split(sep)
            values = [fvalues[i] for i in indexes]
            table.append(Row(*values))
    return table

def writefile(path, table, keys=None, sep=','):
    if keys is None:
        keys = table[0]._fields
    with codecs.open(path, "w", "utf8") as f:
        f.write(sep.join(keys) + '\n')
        for row in table:
            f.write(sep.join(row._asdict()[key] for key in keys) + '\n')

def pprint(table, keys=None):
    if keys is None:
        keys = table[0]._fields
    lens = []
    for k in keys:
        lens.append(len(max([x._asdict()[k] for x in table] + [k], key=len)))
    formats = ["%%-%ds" % length for length in lens]
    pattern = " | ".join(formats)
    separator = "-+-".join(['-' * n for n in lens])
    print(pattern % tuple(keys))
    print(separator)
    for line in table:
        print(pattern % tuple(line._asdict()[k] for k in keys))
