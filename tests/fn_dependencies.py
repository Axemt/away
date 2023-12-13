from away.__fn_utils import __is_away_fn as is_away_fn
from away.__fn_utils import __is_away_protocol_fn as is_away_protocol_fn
from away.__fn_utils import __is_lambda as is_lambda
from away.protocol import __is_repr_literal as is_repr_literal


from away import builder, FaasConnection

faas = FaasConnection(password=1234)

fn_names = faas.get_faas_functions()
assert 'shasum' in fn_names, 'This test needs function \'sleep\' available in FaaS'


import unittest
class TestFnDeps(unittest.TestCase):

    def test_is_lambda(self):

        l = lambda: 1234

        def l2():
            return 1234

        self.assertTrue(is_lambda(l))
        self.assertFalse(is_lambda(l2))

    def test_is_tagged_with_attr(self):

        fn = builder.sync_from_name('shasum', faas)

        self.assertTrue(is_away_fn(fn))

        def fn():
            return 1234

        self.assertFalse(is_away_fn(fn))

        @builder.publish(faas)
        def fn():
            return None

        self.assertTrue(is_away_protocol_fn(fn))

    def test_is_repr_literal(self):

        self.assertTrue( is_repr_literal(1234) )
        self.assertTrue( not is_repr_literal(lambda: 1) )

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

    def test_depends_on_nonproto_intracluster(self):

        intra_dep = builder.sync_from_name('shasum', faas)
        call_arg = 'example.com'

        @builder.publish(faas)
        def echos_nonproto_intracluster_fn(arg):
            return intra_dep(arg)

        base_res = intra_dep(call_arg).strip()
        intracluster_res = echos_nonproto_intracluster_fn(call_arg)
        self.assertEqual(
            intra_dep(call_arg), 
            echos_nonproto_intracluster_fn(call_arg)
        )

    def test_depends_on_proto_intracluster(self):

        call_arg = 'example.com'

        echos_nonproto_intracluster_fn = builder.sync_from_name_with_protocol('echos_nonproto_intracluster_fn', faas)

        @builder.publish(faas)
        def echos_proto_intracluster_fn(arg):
            return echos_nonproto_intracluster_fn(arg)

        self.assertEqual(
            echos_nonproto_intracluster_fn(call_arg),
            echos_proto_intracluster_fn(call_arg)
        )

    @classmethod
    def tearDownClass(cls):
        for name in ['fn', 'uses_outside_dep_fn', 'uses_outside_dep_lambda', 'echos_nonproto_intracluster_fn', 'echos_proto_intracluster_fn']:
            faas.remove_fn(name)