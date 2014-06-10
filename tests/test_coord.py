import unittest

from coral import coord

class TestCoord(unittest.TestCase):

    def test_simplify(self):
        poly = [(-10, -10), (-10, 10), (0, 15), (10, 10), (10, -10), (0, -5)]
        poly = coord.simplify(poly, 10)
        simple = [(-1, -1), (-1, 1), (1, 1), (1, -1)]
        self.assertEqual(poly, simple)

if __name__ == "__main__":
    unittest.main()
