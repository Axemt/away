from away import builder, FaasConnection
import asyncio

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


import unittest
class TestCalls(unittest.TestCase):

    def test_publishes(self):

        @builder.publish(faas, verbose=True)
        def nothing():
            pass

        nothing()
        self.assertTrue(True)

    def test_is_deployed_as_sync_in_server(self):
        
        N = 42656465345

        @builder.publish(faas, verbose=True)
        async def should_be_sync_in_server():
            N = 42656465345
            return N
        # The function is deployed as sync because the runtime on the server is sync
        #  i.e: an async deployment would not work.
        # The stub function wrapped is still async
        res = asyncio.run(should_be_sync_in_server())
        self.assertEqual(res, N)


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


if __name__ == '__main__':
    unittest.main()
