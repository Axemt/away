from away import builder
from away import FaasConnection
from hashlib import sha512

faas = FaasConnection(password='1234')

fn_names = faas.get_faas_functions()
assert 'cows' in fn_names, 'This test needs function \'cows\' available in FaaS'
assert 'shasum' in fn_names, 'This test needs function \'shasum\' available in FaaS'
assert 'nodeinfo' in fn_names, 'This test needs function \'nodeinfo\' available in FaaS'
assert 'env' in fn_names, 'This test needs function \'env\' available in FaaS'
assert 'nslookup' in fn_names, 'This test needs function \'nslookup\' available in FaaS'

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
    verbose=True
)
def env():
    pass

@builder.from_faas_deco(faas,
    implicit_exception_handling=False,
    verbose=True
)
def nslookup(host):
    pass

shasum_from_str = builder.from_faas_str('shasum',
        faas,
        post_cleanup=lambda e: e.strip().replace(' ','').replace('-',''),
        verbose=True
    )

nslookup_from_str = builder.from_faas_str('nslookup',
        faas,
        implicit_exception_handling=False,
        verbose=True
    )

env_from_str = builder.from_faas_str('env',
        faas,
        implicit_exception_handling=False,
        verbose=True
    )


import unittest
class TestCalls(unittest.TestCase):

    def test_plain(self):
        res, status = cows()
        self.assertEqual(status, 200)

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

    def test_from_str_noargs(self):

        res, status = env_from_str()
        self.assertEqual(status, 200)

    def test_onearg(self):

        host = 'www.example.com'
        res, status = nslookup(host)
        self.assertEqual(status, 200)

        res, status = nslookup_from_str(host)
        self.assertEqual(status, 200)


    def test_both_equal(self):

        host = 'www.example.com'

        res_deco, status_deco = nslookup(host)
        res_str,  status_str  = nslookup_from_str(host)

        self.assertEqual(status_deco, status_str)

        s = 'how are you doing?'
        res_deco = shasum(s)
        res_str  = shasum_from_str(s)

        self.assertEqual(res_deco, res_str)


if __name__ == '__main__':
    unittest.main()