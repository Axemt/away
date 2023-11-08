from away import FaasConnection, builder
import inspect

faas = FaasConnection(password='1234')

import unittest
class TestRecursives(unittest.TestCase):

    #def test_recursive_inspect_minimal(self):

    #    def deco(f):
    #        inspect.getclosurevars(f) # ValueError: Cell is empty
    #        return f

    #    @deco
    #    def recursive(n):
    #        if n <= 0 : return n
    #        return recursive(n-1)


    # I yearn for the day when I can remove the line below and know why it happens
    @unittest.expectedFailure
    def test_fibb_in_faas(self):
        
        @builder.publish(faas, verbose=True)
        def fibb(n):
            if n in [0,1]:
                return n
            return fibb(n-1) + fibb(n-2)

        self.assertEqual(fibb(10),55)

    def test_fib_mirror(self):

        def fibb(n):
            if n in [0,1]:
                return n
            return fibb(n-1) + fibb(n-2)
            
        fibb_in_faas = builder.mirror_in_faas(fibb, faas, verbose=True)

        self.assertEqual(fibb_in_faas(10),55)

if __name__ == '__main__':
    unittest.main()