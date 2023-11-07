from away import builder, FaasConnection
import asyncio
from yaml.representer import RepresenterError

faas = FaasConnection(password='1234')

@builder.publish(faas, verbose=True)
def blank():
    return None

@builder.publish(faas, verbose=True)
def sum_one(n):
    return n + 1

@builder.publish(faas, verbose=True)
def sum_some_numbers(one, another):
    return one + another

@builder.publish(faas, verbose=True)
def sum_all_numbers(l):
    res = 0
    for n in l:
        res = res + n

    return res

# requirement for `test_with_global_scope`
SOME_GLOBAL_VAR = 346234624562

# requirement for `test_compatible_from_str`
client_pack_args = builder.__make_client_pack_args(True)
client_unpack_args = builder.__make_client_unpack_args(True)

import unittest
class TestCalls(unittest.TestCase):

    def test_publishes(self):

        @builder.publish(faas, verbose=True)
        def nothing():
            pass

        nothing()
        self.assertTrue(True)

    def test_is_deployed_as_sync_in_server(self):

        el = asyncio.new_event_loop()
        asyncio.set_event_loop(el)

        const = 42656465345

        @builder.publish(faas, verbose=True)
        async def should_be_sync_in_server():
            return const

        # The function is deployed as sync because the runtime on the server is sync
        #  i.e: an async deployment would not work.
        # The stub function wrapped is still async
        res = asyncio.run(should_be_sync_in_server())
        self.assertEqual(res, const)


    def test_plain(self):
        res = blank()
        self.assertEqual(res, None)

    def test_onearg(self):

        N = 4512345234
        res = sum_one(N)
        self.assertEqual(N+1, res)

    def test_twoarg(self):

        A = 25312
        B = 132462346

        res = sum_some_numbers(A,B)
        self.assertEqual(res, A+B)

    def test_iterable(self):

        l = [12354,52345624356,213513456,4256456]

        res = sum_all_numbers(l)
        
        self.assertEqual(res, sum(l))

    def test_with_outside_scope(self):

        nonlocal_var = 234562356256

        @builder.publish(faas, verbose=True)
        def return_the_nonlocal():
            return nonlocal_var

        res = return_the_nonlocal()
        self.assertEqual(res, nonlocal_var)

    def test_with_global_scope(self):

        @builder.publish(faas, verbose=True)
        def return_the_global():
            return SOME_GLOBAL_VAR

        res = return_the_global()
        self.assertEqual(res, SOME_GLOBAL_VAR)
    
    def test_compatible_with_from_str(self):

        sum_one_but_from_str = builder.sync_from_faas_str('sum_one', faas, pack_args=client_pack_args, unpack_args=client_unpack_args, verbose=True)

        self.assertEqual(sum_one(0), 1)
        self.assertEqual(sum_one_but_from_str(0), 1)
        self.assertEqual(sum_one_but_from_str(0), sum_one(0))

    def test_with_unsafe_args(self):

        @builder.publish(faas, safe_args=False, verbose=True)
        def sum_from_range(rg):
            res = 0
            for n in rg:
                res = res + n

            return res

        unsafe_arg = range(10)
        # a Range object is not normally safely unpackable
        self.assertEqual( sum_from_range(unsafe_arg), 45 ) 
        # The same function built with the default safe_args raises an error
        self.assertRaises( RepresenterError, sum_all_numbers, unsafe_arg )


if __name__ == '__main__':
    unittest.main()
