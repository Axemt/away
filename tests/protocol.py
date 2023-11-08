from away import FaasConnection, builder

from away.__protocol import is_repr_literal, pack_repr_or_protocol, safe_server_unpack_args, unsafe_server_unpack_args
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

        self.assertRaises(RepresenterError, pack_repr_or_protocol, lambda e: 1, True)

if __name__ == '__main__':
    unittest.main()
