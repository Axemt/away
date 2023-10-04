from away import FaasConnection



import unittest
class TestConnection(unittest.TestCase):

    def test_constructs(self):
        faas = FaasConnection(ensure_available=False, password=131623564)

    def test_repr(self):
        faas = FaasConnection(provider='lettuce',password='potato', user='tomato', ensure_available=False)

        self.assertEqual('FaasConnection at endpoint: lettuce:8080;\n        Auth details: Present;\n        Is Available: False', str(faas))

    def test_repr_noleak(self):
        password='mysecret'
        user= 'myuser'
        faas = FaasConnection(password=password,user=user)

        self.assertTrue(password not in str(faas))
        self.assertTrue(user not in str(faas))

    def test_get_fns(self):
        faas = FaasConnection(password=1234)
        # this function is ensured to exists thanks to test set-up
        self.assertTrue('shasum' in faas.get_faas_functions())
        self.assertTrue(faas.check_fn_present('shasum'))

    def test_ensure_available(self):
        # ensure available is part of the constructor by default

        available = True
        try:
            faas = FaasConnection(password=1234)
        except:
            available = False
        
        self.assertTrue(available)

        available = True
        try:
            faas = FaasConnection(endpoint='bogus', password=21413423)
        except:
            available = False
        self.assertFalse(available)



if __name__ == '__main__':
    unittest.main()