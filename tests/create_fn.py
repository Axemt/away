from src import builder
from src.FaasConnection import FaasConnection
from hashlib import sha512

faas = FaasConnection(password='1234')

fn_names = faas.get_faas_functions()
assert 'cows' in fn_names, 'This test needs function \'cows\' available in FaaS'
assert 'shasum' in fn_names, 'This test needs function \'shasum\' available in FaaS'


@builder.from_faas_deco(faas, 
    implicit_exception_handling=False,
    verbose=True
)
def cows():
    pass

@builder.from_faas_deco(faas, 
    post_cleanup=lambda e: e.strip().replace(' ','').replace('-',''), 
    verbose=True
)
def shasum(something_to_sha):
    pass

@builder.from_faas_deco(faas,
    implicit_exception_handling=False,
    verbose=True
)
def nodeinfo():
    pass


@builder.from_faas_deco(faas,
    implicit_exception_handling=False,
    verbose=True)
def env():
    pass


import unittest
class TestCalls(unittest.TestCase):

    def test_plain(self):
        res, status = cows()
        self.assertEqual(status, 200)
        # did not crash

    def test_with_cleanup(self):
        s = 'hello'
        res_faas = shasum(s)
        res_local = sha512(str.encode(s)).hexdigest()
        self.assertEqual(res_faas,res_local)

        s = 'hey there'
        res_faas = shasum(s)
        res_local = sha512(str.encode(s)).hexdigest()
        self.assertEqual(res_faas,res_local)

    def test_noargs(self):
        res, status = nodeinfo()
        self.assertEqual(status, 200)

        res, status = env()
        self.assertEqual(status, 200)

if __name__ == '__main__':
    unittest.main()