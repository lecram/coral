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

import collections

def ascii(s):
    src = "áàãâäéèẽêëíìĩîïóòõôöúùũûüç"
    src += src.upper()
    dst = "aaaaaeeeeeiiiiiooooouuuuuc"
    dst += dst.upper()
    return s.translate(str.maketrans(src, dst))

"""
Damerau-Levenshtein Distance:
  + really good for insertion/deletion
  - results not normalized
  - slow
Jaro-Winkler Distance:
  + results normalized
  + fast
  - really bad for insertion/deletion
"""


# Damerau-Levenshtein Distance
def damlev(s1, s2):
    d = {}
    lenstr1 = len(s1)
    lenstr2 = len(s2)
    for i in range(-1,lenstr1+1):
        d[(i,-1)] = i+1
    for j in range(-1,lenstr2+1):
        d[(-1,j)] = j+1
 
    for i in range(lenstr1):
        for j in range(lenstr2):
            if s1[i] == s2[j]:
                cost = 0
            else:
                cost = 1
            d[(i,j)] = min(
                           d[(i-1,j)] + 1, # deletion
                           d[(i,j-1)] + 1, # insertion
                           d[(i-1,j-1)] + cost, # substitution
                          )
            if i and j and s1[i]==s2[j-1] and s1[i-1] == s2[j]:
                d[(i,j)] = min (d[(i,j)], d[i-2,j-2] + cost) # transposition
 
    return d[lenstr1-1,lenstr2-1]

def strerr(s1, s2):
    length = len(s1) + len(s2)
    distance = damlev(s1, s2)
    return distance * 2 / length

# http://en.wikipedia.org/wiki/Jaro%E2%80%93Winkler_distance
def jaro(s1, s2):
    ls1 = len(s1)
    ls2 = len(s2)
    if ls1 < ls2:
        s1 += "*" * (ls2 - ls1)
        length = ls2
    elif ls2 < ls1:
        s2 += "*" * (ls1 - ls2)
        length = ls1
    else:
        length = ls1
    m = 0
    w = length // 2 - 1
    p = []
    for i in range(length):
        if s1[i] == s2[i]:
            m += 1
        else:
            i0, i1 = max(0, i-w), min(length, i+w+1)
            f = s2.find(s1[i], i0, i1)
            if f >= 0:
                m += 1
                p.append(f)
    if m == 0:
        return 0
    t = 0
    x = 0
    for f in p:
        if f < x:
            t += 1
        else:
            x = f
    return (m / ls1 + m / ls2 + (m - t) / m) / 3

# http://en.wikipedia.org/wiki/Jaro%E2%80%93Winkler_distance
def jaro_winkler(s1, s2):
    L = 0
    prelen = min([len(s1), len(s2), 4])
    for c1, c2 in zip(s1[:prelen], s2[:prelen]):
        if c1 == c2:
            L += 1
        else:
            break
    j = jaro(s1, s2)
    return j + (L * 0.1 * (1 - j))

def mapping(keys, values):
    Match = collections.namedtuple("Match", "key, value, score")
    m = []
    for key in keys:
        ds = [strerr(key, value) for value in values]
        i = min(range(len(values)), key=ds.__getitem__)
        value = values[i]
        score = 1 - ds[i]
        m.append(Match(key, value, score))
    m.sort(key=lambda match: -match.score)
    return m

def abbreviations(names, length):
    norm = lambda name: ascii(name.upper())
    inames = [(i, norm(name)) for i, name in enumerate(names)]
    inames.sort(key=len)
    counter = collections.Counter()
    for i, name in inames:
        counter.update(set(name))
    hist = dict(counter)
    abbdict = {}
    abbset = set()
    for i, name in inames:
        tname = name[:]
        for extra in extras:
            tname = tname.replace(" {} ".format(extra), " ")
        if len(tname) <= length:
            abb = tname
        else:
            ics = list(enumerate(tname))
            initis = [0] + [i+1 for i, c in ics if c == " "]
            #for j in range(len(initis)):
            #    initis[j] -= j
            ics = [(i, c) for i, c in ics if c != " "]
            ics.sort(key=lambda ic: hist[ic[1]])
            for j, initi in enumerate(initis):
                ic = (initi, tname[initi])
                ics.remove(ic)
                ics.insert(j, ic)
            for comb in itertools.combinations(ics, length):
                comb = list(comb)
                comb.sort(key=lambda ic: ic[0])
                abb = "".join(c for i, c in comb)
                if abb not in abbset:
                    break
            else:
                raise Exception("unable to generate unique abbreviation")
        abbdict[i] = abb
        abbset.add(abb)
    return {name: abbdict[i] for i, name in enumerate(names)}

if __name__ == "__main__":
    l1 = ['abc', 'def', 'ghi', 'jkl']
    l2 = ['ac', 'def', 'gh', 'jekgl']
    print(mapping(l1, l2))
