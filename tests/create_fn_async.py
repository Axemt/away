from away import builder_async, builder
from away import FaasConnection
from time import time
import asyncio
import warnings
from hashlib import sha512

faas = FaasConnection(password='1234')

fn_names = faas.get_faas_functions()
assert 'sleep' in fn_names, 'This test needs function \'sleep\' available in FaaS'
assert 'shasum' in fn_names, 'This test needs function \'shasum\' available in FaaS'

@builder_async.from_faas_deco(faas, verbose=True)
def sleep(): # sleeps for 2s
    pass

@builder_async.from_faas_deco(faas, verbose=True)
def nmap(domain):
    pass


shasum_cleanup = lambda e: e.strip().replace(' ','').replace('-','')
@builder_async.from_faas_deco(faas,
    post_cleanup=shasum_cleanup,
    verbose=True
)
def shasum(s):
    pass

shasum_faas_sync = builder.from_faas_str('shasum',
    faas, 
    verbose=True, 
    post_cleanup=shasum_cleanup
)


import unittest
class TestCalls(unittest.IsolatedAsyncioTestCase):

    async def test_plain_to_completion(self):
        t = time()
        fut = sleep()
        self.assertTrue( time() - t < 2 )
        await fut
        self.assertTrue( time() - t > 2)

    async def test_noawait(self):
        t = time()
        sleep()
        sleep()
        sleep()

        self.assertTrue( time() - t < 2 )

    async def test_results(self):
        
        s = 'hello'
        res_faas  = await shasum(s)
        res_local = sha512(str.encode(s)).hexdigest()

        self.assertEqual(res_faas, res_local)

    async def test_results_equal_sync(self):

        s = 'goodbye'

        res_sync  = shasum_faas_sync(s)
        res_async = await shasum(s)

        self.assertEqual(res_sync, res_async)

    async def test_from_str(self):

        time_async = builder_async.from_faas_str('sleep', faas, verbose=True)
        t = time()
        await time_async()
        self.assertTrue(time() - t > 2)


if __name__ == '__main__':
    unittest.main()