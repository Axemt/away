from away import builder, FaasConnection
from time import time
import asyncio
import warnings
from hashlib import sha512
import inspect

faas = FaasConnection(password='1234')

fn_names = faas.get_faas_functions()
assert 'sleep' in fn_names, 'This test needs function \'sleep\' available in FaaS'
assert 'shasum' in fn_names, 'This test needs function \'shasum\' available in FaaS'

@builder.faas_function(faas, verbose=True)
async def sleep(): # sleeps for 2s
    pass

@builder.faas_function(faas, verbose=True)
async def nmap(domain):
    pass


shasum_unpack = lambda e: e.strip().replace(' ','').replace('-','')
@builder.faas_function(faas,
    unpack_args=shasum_unpack,
    verbose=True
)
async def shasum(s):
    pass

shasum_faas_sync = builder.sync_from_faas_str('shasum',
    faas, 
    verbose=True, 
    unpack_args=shasum_unpack
)

sleep_faas_async = builder.async_from_faas_str('sleep', faas, verbose=True)


import unittest
class TestCalls(unittest.IsolatedAsyncioTestCase):

    async def test_dispatches_async(self):

        self.assertTrue(inspect.iscoroutinefunction(sleep_faas_async))
        self.assertTrue(inspect.iscoroutinefunction(sleep))

    async def test_plain_to_completion(self):
        t = time()
        fut = sleep()
        self.assertTrue( time() - t < 2 )
        await fut
        self.assertTrue( time() - t > 2)

    async def test_noawait(self):
        # ending a function when futures are still running raises a warning. this is intentional by the test's design
        warnings.filterwarnings('ignore')
        t = time()

        sleep()
        sleep()
        sleep()

        self.assertTrue( time() - t < 2 )
        warnings.filterwarnings('default')

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
        t = time()
        await sleep_faas_async()
        self.assertTrue(time() - t > 2)

    async def test_exceptions(self):

        nmap_with_except = builder.async_from_faas_str('nmap', faas, verbose=True, implicit_exception_handling=False)

        res, status = await nmap_with_except('upv.es')
        self.assertEqual(status, 200)


if __name__ == '__main__':
    unittest.main()