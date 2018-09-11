import os
import sys
import unittest
import random
import string
from redisgraph import Graph, Node, Edge

from .disposableredis import DisposableRedis
from base import FlowTestsBase

redis_graph = None
labels = ["label_a", "label_b"]
fields = ['unique', 'group', 'doubleval', 'intval', 'stringval']
groups = ["Group A", "Group B", "Group C","Group D", "Group E"]
node_ctr = 0

def redis():
    return DisposableRedis(loadmodule=os.path.dirname(os.path.abspath(__file__)) + '/../../src/redisgraph.so')

class IndexUpdatesFlowTest(FlowTestsBase):

    @classmethod
    def setUpClass(cls):
        print "IndexUpdatesFlowTest"
        global redis_graph
        cls.r = redis()
        cls.r.start()
        redis_con = cls.r.client()
        redis_graph = Graph("index_test", redis_con)
        cls.populate_graph()
        cls.build_indices()

    @classmethod
    def tearDownClass(cls):
        cls.r.stop()

    @classmethod
    def new_node(self):
        return Node(label = labels[node_ctr % 2],
                    properties = {'unique': node_ctr,
                                  'group': random.choice(groups),
                                  'doubleval': round(random.uniform(-1, 1), 2),
                                  'intval': random.randint(1, 10000),
                                  'stringval': ''.join(random.choice(string.lowercase) for x in range(6))})
    @classmethod
    def populate_graph(self):
        global node_ctr
        for i in range(1000):
            node = self.new_node()
            redis_graph.add_node(node)
            node_ctr += 1
        redis_graph.commit()
    
    @classmethod
    def build_indices(self):
        for field in fields:
            redis_graph.redis_con.execute_command("GRAPH.QUERY", "index_test", "CREATE INDEX ON :label_a(%s)" % (field))
            redis_graph.redis_con.execute_command("GRAPH.QUERY", "index_test", "CREATE INDEX ON :label_b(%s)" % (field))

    # Validate that all properties are indexed
    def validate_indexed(self):
        for field in fields:
            # Empty string causing connection error?
            #  resp = redis_graph.execution_plan("""MATCH (a:label_a) WHERE a.%s > '' RETURN a""" % (field))
            resp = redis_graph.execution_plan("""MATCH (a:label_a) WHERE a.%s > 0 RETURN a""" % (field))
            self.assertIn('Index Scan', resp)

    # So long as 'unique' is not modified, label_a.unique will always be even and label_b.unique will always be odd
    def validate_unique(self):
        result = redis_graph.query("MATCH (a:label_a) RETURN a.unique")
        # Remove the header
        result.result_set.pop(0)
        for val in result.result_set:
            assert(int(float(val[0])) % 2 == 0)

        result = redis_graph.query("MATCH (b:label_b) RETURN b.unique")
        # Remove the header
        result.result_set.pop(0)
        for val in result.result_set:
            assert(int(float(val[0])) % 2 == 1)

    # The index scan ought to return identical results to a label scan over the same range of values.
    def validate_doubleval(self):
        for label in ["label_a", "label_b"]:
            resp = redis_graph.execution_plan("""MATCH (a:%s) WHERE a.doubleval < 100 RETURN a.doubleval ORDER BY a.doubleval""" % (label))
            self.assertIn('Index Scan', resp)
            indexed_result = redis_graph.query("""MATCH (a:%s) WHERE a.doubleval < 100 RETURN a.doubleval ORDER BY a.doubleval""" % (label))
            scan_result = redis_graph.query("""MATCH (a:%s) RETURN a.doubleval ORDER BY a.doubleval""" % (label))
            # TODO can encounter errors of the type:
            #  First differing element 259:
            #  ['0.000000']
            #  ['-0.000000']
            self.assertEqual(indexed_result.result_set, scan_result.result_set)

    # Validate a series of premises to ensure that the graph has not been modified unexpectedly
    def validate_state(self):
        self.validate_unique()
        self.validate_indexed()
        self.validate_doubleval()

    # Modify a property, triggering updates to all nodes in two indices
    def test_full_property_update(self):
        result = redis_graph.query("MATCH (a) SET a.doubleval = a.doubleval + %f" % (round(random.uniform(-1, 1), 2)))
        assert(result.properties_set == 1000)
        # Verify that index scans still function and return correctly
        self.validate_state()

    # Modify a property, triggering updates to a subset of nodes in two indices
    def test_partial_property_update(self):
        redis_graph.query("MATCH (a) WHERE a.doubleval > 0 SET a.doubleval = a.doubleval + %f" % (round(random.uniform(-1, 1), 2)))
        # Verify that index scans still function and return correctly
        self.validate_state()

    #  Add 100 randomized nodes and validate indices
    def test_node_creation(self):
        # Reset nodes in the Graph object so that we won't double-commit the originals
        redis_graph.nodes = {}
        global node_ctr
        for i in range(100):
            node = self.new_node()
            redis_graph.add_node(node)
            node_ctr += 1
        redis_graph.commit()
        self.validate_state()

    # Delete random nodes and validate indices
    def test_node_deletion(self):
        # Reset nodes in the Graph object so that we won't double-commit the originals
        redis_graph.nodes = {}
        global node_ctr
        # Delete nodes one at a time
        for i in range(500):
            id_to_delete = random.randrange(0, node_ctr)
            result = redis_graph.query("MATCH (a) WHERE ID(a) = %d DELETE a" % (id_to_delete))
            assert(result.nodes_deleted == 1)
            node_ctr -= 1
        self.validate_state()
        # Delete all nodes matching a filter

if __name__ == '__main__':
    unittest.main()