from away import builder, FaasConnection
from away.__fn_utils import __is_lambda as is_lambda

faas = FaasConnection(password=1234)

nonrepr = map(int, "1234")

import unittest
class TestExternalObjs(unittest.TestCase):

    def test_pulls_in_non_repr_dep(self):

        @builder.publish(faas, verbose=True)
        def sum_nonrepr():
            return sum(list(nonrepr))

        self.assertEqual(sum_nonrepr(), sum(list(nonrepr)))

    def test_is_lambda(self):

        def a():
            return 0

        b = lambda: 1

        self.assertTrue(not is_lambda(a))
        self.assertTrue(is_lambda(b))

    def test_chain_dep(self):

        secret = 321352345
        def uses_dep():
            return secret

        @builder.publish(faas, verbose=True)
        def uses_chain():
            return uses_dep()

        self.assertEqual(uses_chain(), secret)

if __name__ == '__main__':
    unittest.main()