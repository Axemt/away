from away import FaasConnection

import unittest
class TestConnection(unittest.TestCase):

    def test_constructs(self):
        faas = FaasConnection(ensure_available=False, password=131623564)

    def test_ensure_auth_fails(self):
        faas = FaasConnection(ensure_available=False)

        self.assertRaises(Exception, faas.ensure_auth)

    def test_repr(self):
        faas = FaasConnection(provider='lettuce',password='potato', user='tomato', ensure_available=False)

        self.assertEqual('FaasConnection at endpoint: lettuce:8080;\n        Auth details: Not logged in;\n        Is Available: False', str(faas))

    def test_repr_noleak(self):
        password='mysecret'
        user= 'myuser'
        faas = FaasConnection(password=password,user=user, ensure_available=False)

        self.assertTrue(password not in str(faas))
        self.assertTrue(user not in str(faas))

    def test_get_fns(self):
        faas = FaasConnection(password=1234)
        # this function is ensured to exists thanks to test set-up
        self.assertTrue('shasum' in faas.get_faas_functions())
        self.assertTrue(faas.check_fn_present('shasum'))

    def test_ensure_available(self):
        # ensure available is part of the constructor by default

        faas = FaasConnection(password=1234)
        faas.ensure_available()
        faas = FaasConnection(endpoint='bogus', password=21413423)
        self.assertRaises(Exception, faas.ensure_available)



if __name__ == '__main__':
    unittest.main()