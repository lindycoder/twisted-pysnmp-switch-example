import unittest

from mock import MagicMock
from pyasn1.type import univ

from snmp.oid_store import UnknownOID, NoNextOID, OIDStore, is_a_descendant_or_same, \
    is_a_descendant


class TestOIDStoreTest(unittest.TestCase):
    def test_get_exact_oid(self):
        store = OIDStore({(1, 2, 3): univ.Integer(99)})

        result = store.get((1, 2, 3))

        self.assertEqual((1, 2, 3), result[0])
        self.assertEqual(univ.Integer(99), result[1])

    def test_get_exact_oid_with_unknown(self):
        store = OIDStore({})

        with self.assertRaises(UnknownOID):
            store.get((9, 9, 9))

    def test_next_oid(self):
        store = OIDStore({(1, 2, 3): univ.Integer(99),
                          (1, 2, 4): univ.Integer(100)})

        result = store.get_next((1, 2, 3))

        self.assertEqual((1, 2, 4), result[0])
        self.assertEqual(univ.Integer(100), result[1])

    def test_next_oid_when_last(self):
        store = OIDStore({(1, 2, 3): univ.Integer(99)})

        with self.assertRaises(NoNextOID):
            store.get_next((1, 2, 3))

    def test_next_oid_when_oid_doesnt_exists(self):
        store = OIDStore({(1, 2, 4): univ.Integer(100)})

        result = store.get_next((1, 2, 3))

        self.assertEqual((1, 2, 4), result[0])
        self.assertEqual(univ.Integer(100), result[1])

    def test_next_oid_when_value_is_lambda_get_called(self):
        mock_lambda = MagicMock(return_value=univ.Integer(99))
        store = OIDStore({(1, 2, 2): None,
                          (1, 2, 3): mock_lambda})

        result = store.get_next((1, 2, 2))

        self.assertEqual(univ.Integer(99), result[1])
        mock_lambda.assert_called_with((1, 2, 3), store)

    def test_set_oid_changes_get_value(self):
        store = OIDStore({(1, 2, 3): univ.Integer(100)})

        store.set((1, 2, 3), univ.Integer(99))

        self.assertEqual(((1, 2, 3), univ.Integer(99)), store.get((1, 2, 3)))

    def test_set_unknown_value_creates_it(self):
        store = OIDStore({})

        with self.assertRaises(UnknownOID):
            store.set((1, 2, 3), univ.Integer(99))

    def test_oid_is_a_descendant_or_same(self):
        self.assertTrue(is_a_descendant_or_same((1,), (1,)))
        self.assertTrue(is_a_descendant_or_same((1, 2), (1,)))
        self.assertFalse(is_a_descendant_or_same((1, 2), (2,)))
        self.assertFalse(is_a_descendant_or_same((1,), (1, 2)))
        self.assertTrue(is_a_descendant_or_same((1, 2, 3, 1), (1,)))

    def test_oid_is_a_descendant(self):
        self.assertFalse(is_a_descendant((1,), (1,)))
        self.assertTrue(is_a_descendant((1, 2), (1,)))
        self.assertFalse(is_a_descendant((1, 2), (2,)))
        self.assertFalse(is_a_descendant((1,), (1, 2)))
        self.assertTrue(is_a_descendant((1, 2, 3, 1), (1,)))

    def test_get_supports_lambda(self):
        mock_lambda = MagicMock(return_value=univ.Integer(99))
        store = OIDStore({(1, 2, 3): mock_lambda})

        result = store.get((1, 2, 3))

        self.assertEqual(univ.Integer(99), result[1])
        mock_lambda.assert_called_with((1, 2, 3), store)
