import unittest

from coral import coord

class TestCoord(unittest.TestCase):

    def test_simplify(self):
        poly = [(-10, -10), (-10, 10), (0, 13), (10, 10), (10, -10), (0, -7)]
        poly = list(coord.simplify(poly, 10))
        simple = [(-1, -1), (-1, 1), (1, 1), (1, -1)]
        self.assertEqual(poly, simple[1:] + simple[:1])

if __name__ == "__main__":
    unittest.main()
