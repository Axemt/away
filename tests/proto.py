from away import FaasConnection, builder

from away.protocol import make_client_pack_args_fn, make_client_unpack_args_fn
from away.protocol import __is_repr_literal as is_repr_literal
from away.protocol import __pack_repr_or_protocol as pack_repr_or_protocol
from away.protocol import __safe_server_unpack_args as safe_server_unpack_args
from away.protocol import __unsafe_server_unpack_args as unsafe_server_unpack_args
import inspect
from yaml.representer import RepresenterError 

faas = FaasConnection(password='1234')

import unittest
class TestProtocol(unittest.TestCase):
    
    def test_is_repr_literal(self):

        self.assertTrue( is_repr_literal(1234) )
        self.assertTrue( not is_repr_literal(lambda: 1) )

    def test_packs_repr(self):

        self.assertEqual( pack_repr_or_protocol(1234, False), repr(1234) )
        # the result should be independent on if the args are safe or not
        self.assertEqual( pack_repr_or_protocol(1234, True), repr(1234) )

    def test_pack_repr_raises(self):

        self.assertRaises(RepresenterError, pack_repr_or_protocol, map(lambda e: 1, "123"), True)

    def test_safe_protocol(self):

        args = (1,2,3,"a")
        pack = make_client_pack_args_fn(safe_args=True)

        packed_safe_args = pack(args)

        # NOTE: *_server_unpack_args returns the list of args and their length
        #        to verify it.
        server_side_args, _ = safe_server_unpack_args(packed_safe_args)


        self.assertEqual(tuple(server_side_args), args)

    def test_unsafe_protocol(self):

        args = (1,2, range(10), "aaaaaa", "a")
        pack = make_client_pack_args_fn(safe_args=False)

        packed_unsafe_args = pack(args)
        server_side_args, _ = unsafe_server_unpack_args(packed_unsafe_args)
        
        self.assertEqual(tuple(server_side_args), args)

    def test_external_fn_dependency(self):

        def outside_dep_fn():
            return 1

        @builder.publish(faas, verbose=True)
        def uses_outside_dep_fn(n):
            return n + outside_dep_fn()

        self.assertEqual(uses_outside_dep_fn(1), 2)

        
    def test_external_lambda_dependency(self):

        outside_dep_lambda = lambda: 1

        @builder.publish(faas, verbose=True)
        def uses_outside_dep_lambda(n):
            return n + outside_dep_lambda()

        self.assertEqual(uses_outside_dep_lambda(1), 2)

    def test_faas_from_str_with_protocol(self):

        @builder.publish(faas)        
        def sums_one(n):
            return n + 1

        faas_fn = builder.sync_from_faas_str_with_protocol('sums_one', faas)

        self.assertEqual( sums_one(0), faas_fn(0) )

    def test_blank_deco_with_protocol(self):

        @builder.faas_function_with_protocol(faas)
        def fibb(n):
            pass
        
        self.assertEqual(fibb(10), 55)

if __name__ == '__main__':
    unittest.main()
