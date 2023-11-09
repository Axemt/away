from away import builder, FaasConnection
from away.__fn_utils import __is_lambda as is_lambda

faas = FaasConnection(password=1234)

nonrepr = map(lambda e: int(e), "1234")

import unittest
class TestExternalObjs(unittest.TestCase):

    def test_pulls_in_non_repr_dep(self):

        @builder.publish(faas, verbose=True, safe_args=False)
        def sum_nonrepr():
            return sum(list(nonrepr))

    def test_raises_if_not_safe_args(self):

        def sum_nonrepr():
            return sum(list(nonrepr))

        self.assertRaises(Exception, builder.mirror_in_faas, sum_nonrepr, faas) 

    def test_is_lambda(self):

        def a():
            return 0

        b = lambda: 1

        self.assertTrue(not is_lambda(a))
        self.assertTrue(is_lambda(b))

if __name__ == '__main__':
    unittest.main()