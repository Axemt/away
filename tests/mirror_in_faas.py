from away import FaasConnection, builder

faas = FaasConnection(password='1234')

import unittest
class TestMirrors(unittest.TestCase):

    def test_mirrors_in_faas(self):

        secret = 266423
        def add_secret_number(it):
            for i in range(len(it)):
                it[i] += secret
            return it

        add_secret_number_in_faas = builder.mirror_in_faas(add_secret_number, faas, verbose=True)


        self.assertEqual( add_secret_number([1,2,3]), add_secret_number_in_faas([1,2,3]) )


if __name__ == '__main__':
    unittest.main()