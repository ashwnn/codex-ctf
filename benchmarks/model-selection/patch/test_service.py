import unittest

from service import read_record


class ContractTests(unittest.TestCase):
    def test_owner_can_read(self):
        self.assertEqual(
            read_record("r-1", "alice"),
            (200, {"id": "r-1", "body": "synthetic-alpha"}),
        )


if __name__ == "__main__":
    unittest.main()
