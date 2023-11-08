from away import builder, FaasConnection

faas = FaasConnection(password=1234)


import unittest
class TestExternalObjs(unittest.TestCase):

    def pulls_in_non_repr_dep(self):

        nonrepr = map(lambda e: int(e), "1234")

        @builder.publish(faas, verbose=True, safe_args=False)
        def sum_nonrepr():
            return sum(list(nonrepr))


