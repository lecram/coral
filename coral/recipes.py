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

/////

"""
Do not run this file. It's saved with PY extension in order to trigger syntax
 highlighting. The line above is intended to cause a syntax error in case of
 acidental execution. Leave it there.
"""

"""
Generating a simple map of Brazilian states.
"""

from coral import table, pf, coord, vector, tqdm

# Pixel size, in meters.
# Adjust this to change the map resolution.
pixsz = 5000

# Map projection.
proj = coord.Mercator()

# Load data.
ufs = table.readfile("uf.csv")
pff = pf.Reader("uf.p")

# Create blank page.
page = vector.Page()

# Draw borders to page.
for uf in tqdm.tqdm(ufs):
    for poly in pff.get(uf.uf_id):
        poly = [proj.geo2rect(lon, lat) for lon, lat in poly]
        poly = coord.simplify(poly, pixsz)
        if len(poly) < 3: continue
        page.addpolygon(poly, stroke=0)

# Save map.
page.export("brazil.png", "pngmono", margin=5)

"""
Converting a shapefile to P format.
"""

from coral import shapefile, table, pf, stats

biomas = table.readfile("../div/bioma.csv")

pff = pf.Writer("bioma.p", 4)
sf = shapefile.Reader("/media/STONE/data/ibge/biomas/Biomas5000")
for sr in sf.shapeRecords():
    bioma = table.getone(biomas, "bio_code", sr.record[0])
    if bioma is None:
        continue
    name = bioma.bio_id
    points = sr.shape.points
    offsets = list(sr.shape.parts) + [len(points)]
    parts = [points[a:b] for a, b in zip(offsets[:-1], offsets[1:])]
    pff.write(name, parts)
errs = pff.close()
print("avg:", stats.avg(errs))
print("max:", stats.max(errs))
