from away import builder, FaasConnection
from away.exceptions import EnsureException

faas = FaasConnection(password=1234)

class T:

    def static_fn_part_of_class(n):
        return n+1
    
    def class_method(self, n):
        return n+1

import unittest
class TestStateless(unittest.TestCase):

    def test_with_instance_raises(self):

        self.assertRaises(EnsureException, builder.mirror_in_faas, T().static_fn_part_of_class, faas)
        self.assertRaises(EnsureException, builder.mirror_in_faas, T().class_method, faas)

    def test_from_uninstanced_doesnt_take_self(self):

        static_fn = builder.mirror_in_faas(T.static_fn_part_of_class, faas, verbose=True)
        self.assertEqual(static_fn(1), 2)

    def test_from_uninstanced_takes_self(self):

        self.assertRaises(EnsureException, builder.mirror_in_faas, T.class_method, faas)

if __name__ == '__main__':
    unittest.main()