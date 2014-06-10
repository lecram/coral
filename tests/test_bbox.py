import math
import random
import unittest

from coral import bbox

class TestBBox(unittest.TestCase):

    def setUp(self):
        self.a = bbox.BBox((20, 30), (50, 40))
        self.b = self.a.scale(2)
        self.c = self.b.translate(self.b.width() / 2, 0)

    def test_bounding(self):
        cx, cy = random.randint(-100, 100), random.randint(-100, 100)
        r = random.randint(20, 100)
        bb1 = bbox.BBox((cx-r, cy-r), (cx+r, cy+r))
        n = 1000
        t = 2 * math.pi
        x = (cx + r * math.cos(t*i/n) for i in range(n))
        y = (cy + r * math.sin(t*i/n) for i in range(n))
        ps = zip(x, y)
        bb2 = bbox.BBox(ps)
        self.assertEqual(bb1, bb2)

    def test_width_height_area(self):
        self.assertEqual(self.a.area(), self.a.width() * self.a.height())

    def test_scale_area(self):
        self.assertEqual(self.a.area() * 4, self.b.area())

    def test_scale_center(self):
        self.assertEqual(self.a.center(), self.b.center())

    def test_translate_area_union(self):
        self.assertEqual((self.b | self.c).area(), self.b.area() * 3 / 2)

    def test_translate_area_intersection(self):
        self.assertEqual((self.b & self.c).area(), self.b.area() / 2)

    def test_haspoint(self):
        self.assertTrue(self.a.has_point(self.a.center()))
        half_width = self.a.width() / 2
        half_height = self.a.height() / 2
        for dx, dy in ((-half_width, 0), (0, -half_height), (-half_width, -half_height)):
            self.assertTrue(self.a.has_point(self.a.translate(dx, dy).center()))
        for dx, dy in ((half_width, 0), (0, half_height), (half_width, half_height)):
            self.assertFalse(self.a.has_point(self.a.translate(dx, dy).center()))

    def test_hasbbox(self):
        self.assertFalse(self.a.has_bbox(self.b))
        self.assertTrue(self.b.has_bbox(self.a))

    def test_compare(self):
        self.assertEqual(self.a, self.a.scale(1))
        self.assertNotEqual(self.a, self.a.scale(1.2))
        self.assertNotEqual(self.a, self.a.scale(0.8))
        self.assertTrue(self.a < self.b)

if __name__ == "__main__":
    unittest.main()
