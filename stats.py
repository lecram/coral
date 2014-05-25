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
Cached statistical computations.
"""

import math
import functools
import collections

memoize = functools.lru_cache

max = memoize()(max)
min = memoize()(min)
sum = memoize()(math.fsum)
len = memoize()(len)

@memoize(maxsize=128)
def avg(seq):
    return sum(seq) / len(seq)

@memoize(maxsize=64)
def var(seq):
    u = avg(seq)
    return sum((x - u) * (x - u) for x in seq) / len(seq)

@memoize(maxsize=64)
def std_dev(seq):
    return math.sqrt(var(seq))

@memoize(maxsize=32)
def covar(seq1, seq2):
    n = len(seq1)
    u1 = avg(seq1)
    u2 = avg(seq2)  
    cov = 0
    for i in range(n):
        a = seq1[i] - u1            
        b = seq2[i] - u2
        cov += a * b / n
    return cov

@memoize(maxsize=16)
def corr(seq1, seq2):
    return covar(seq1, seq2) / (std_dev(seq1) * std_dev(seq2))

# Kakwani, N. C. (1980). Inequality and Poverty: methods of estimation and policy applications. New York: World Bank; Oxford University Press.
# http://www.ipea.gov.br/portal/index.php?option=com_content&view=article&id=18285
@memoize(maxsize=16)
def gini_kakwani(seq):
    n = len(seq)
    u = avg(seq)
    s = 0
    for i in range(n):
        for j in range(i + 1, n):
            s += abs(seq[i] - seq[j])
    us = 2 * s / (n * (n - 1))
    g = us / (2 * u)
    return g

# Deaton, Angus (1997). Analysis of Household Surveys. Baltimore MD: Johns Hopkins University Press. ISBN 0-585-23787-5.
# http://en.wikipedia.org/wiki/Gini_coefficient#Calculation
@memoize(maxsize=16)
def gini_deaton(seq):
    n = len(seq)
    u = avg(seq)
    s = sum(seq)
    seq = tuple(sorted(seq, reverse=True))
    for i, x in enumerate(seq):
        s += i * x
    g = (n + 1) / (n - 1) - 2 * s / (n * (n - 1) * u)
    return g

memos = [sum, len, avg, var, std_dev, covar, corr, gini_kakwani, gini_deaton]

CacheInfo = collections.namedtuple("CacheInfo", "hits, misses, maxsize, currsize")

def cache_clear():
    for memo in memos:
        memo.cache_clear()

def cache_info():
    total_hits, total_misses, total_maxsize, total_currsize = 0, 0, 0, 0
    for memo in memos:
        hits, misses, maxsize, currsize = memo.cache_info()
        total_hits      += hits
        total_misses    += misses
        total_maxsize   += maxsize
        total_currsize  += currsize
    return CacheInfo(total_hits, total_misses, total_maxsize, total_currsize)

if __name__ == "__main__":
    import random
    inc = (1000, 200, 1000, 2000, 600)
    inc = tuple(map(lambda x: random.random(), range(10000)))
    print(gini_kakwani(inc))
    print(gini_deaton(inc))
    print(cache_info())
