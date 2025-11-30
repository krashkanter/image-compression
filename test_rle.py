import unittest
import random
from utils import rle_encode, rle_decode

class TestRLE(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle_encode(b""), b"")
        self.assertEqual(rle_decode(b""), b"")

    def test_literals(self):
        data = b"abcdef"
        encoded = rle_encode(data)
        # Should be 1 literal run of 6: control byte 5
        self.assertEqual(encoded, b"\x05abcdef")
        decoded = rle_decode(encoded)
        self.assertEqual(decoded, data)

    def test_repeat(self):
        data = b"aaaaa"
        encoded = rle_encode(data)
        # Run of 5: control byte 126 + 5 = 131
        self.assertEqual(encoded, bytes([131, ord('a')]))
        decoded = rle_decode(encoded)
        self.assertEqual(decoded, data)

    def test_mixed(self):
        data = b"abc" + b"d" * 10 + b"efg"
        encoded = rle_encode(data)
        decoded = rle_decode(encoded)
        self.assertEqual(decoded, data)

    def test_long_run(self):
        data = b"a" * 200
        encoded = rle_encode(data)
        decoded = rle_decode(encoded)
        self.assertEqual(decoded, data)

    def test_random(self):
        for _ in range(100):
            data = bytes(random.getrandbits(8) for _ in range(1000))
            encoded = rle_encode(data)
            decoded = rle_decode(encoded)
            self.assertEqual(decoded, data)

    def test_boundaries(self):
        # Test max literal run (128 bytes)
        data = bytes(range(128))
        encoded = rle_encode(data)
        # Control byte 127 (128-1) followed by data
        self.assertEqual(encoded[0], 127)
        self.assertEqual(len(encoded), 129)
        self.assertEqual(rle_decode(encoded), data)

        # Test max literal run + 1 (129 bytes) -> should be split
        data = bytes(range(129))
        encoded = rle_encode(data)
        # Should be 128 literals (control 127) + 1 literal (control 0)
        # Or however the greedy algorithm handles it.
        # My algo: greedy takes 128. Then 1 left.
        self.assertEqual(encoded[0], 127)
        self.assertEqual(encoded[129], 0)
        self.assertEqual(rle_decode(encoded), data)

        # Test max repeat run (129 bytes)
        data = b"A" * 129
        encoded = rle_encode(data)
        # Control byte 255 (126 + 129) followed by "A"
        self.assertEqual(encoded, bytes([255, ord("A")]))
        self.assertEqual(rle_decode(encoded), data)

        # Test max repeat run + 1 (130 bytes)
        data = b"A" * 130
        encoded = rle_encode(data)
        # Should be Run(129) + Literal(1)
        self.assertEqual(encoded[0], 255)
        self.assertEqual(encoded[2], 0) # Control for 1 literal
        self.assertEqual(encoded[3], ord("A"))
        self.assertEqual(rle_decode(encoded), data)

if __name__ == "__main__":
    unittest.main()
