from away import FaasConnection
from away.exceptions import EnsureException, FaasServiceUnavailableException

import unittest
class TestConnection(unittest.TestCase):

    def test_constructs(self):
        faas = FaasConnection(ensure_available=False, password=131623564)

    def test_ensure_auth_fails(self):
        faas = FaasConnection(ensure_available=False)

        self.assertRaises(EnsureException, faas.ensure_auth)

    def test_ensure_fn_present(self):

        faas = FaasConnection(password=1234)
        self.assertRaises(EnsureException, faas.ensure_fn_present, 'non_existent_function')

    def test_repr(self):
        faas = FaasConnection(provider='lettuce',password='potato', user='tomato', ensure_available=False, server_architecture='lol')

        self.assertEqual('FaasConnection at endpoint: lettuce:8080;\n        Arch: lol,\n        Auth details: Not logged in,\n        Is Available: False', str(faas))

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
        faas = FaasConnection(provider='does_not_exist', password=21413423, ensure_available=False)
        self.assertRaises(FaasServiceUnavailableException, faas.ensure_available)

    def test_get_annotations(self):

        faas = FaasConnection(password=1234)
        annotations = faas.get_function_annotations('shasum')

        unauth_faas = FaasConnection()
        self.assertRaises(EnsureException, unauth_faas.get_function_annotations, 'shasum')

    def test_is_away_protocol(self):

        faas = FaasConnection(password=1234)

        self.assertTrue(not faas.is_away_protocol('shasum'))

if __name__ == '__main__':
    unittest.main()