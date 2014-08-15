import unittest

from coral import coord

class TestCoord(unittest.TestCase):

    def test_buffer(self):
        N = 4
        self.assertTrue(N > 2)
        b = coord.Buffer(N)
        self.assertTrue(b.isempty())
        self.assertFalse(b.isfull())
        b.push(5)
        b.push(7)
        self.assertFalse(b.isempty())
        self.assertFalse(b.isfull())
        self.assertEqual(b.pop(), 7)
        b.push(11)
        self.assertEqual(b.shift(), 5)
        self.assertEqual(b.shift(), 11)
        for i in range(23):
            if b.isfull():
                b.shift()
            b.push(i)
        self.assertFalse(b.isempty())
        self.assertTrue(b.isfull())
        self.assertEqual(b.pop(), 22)
        self.assertEqual(b.shift(), 19)
        self.assertEqual(b.shift(), 20)
        self.assertEqual(b.pop(), 21)
        self.assertTrue(b.isempty())
        self.assertFalse(b.isfull())

if __name__ == "__main__":
    unittest.main()
