from cube import *

def test_edge_vertex_isomorphism():
    for rot in [-1, 1]:
        vv = Vertex(Cube(0,0,0),rot)
        for v,e in vv.edge_vertices():
            a,b = e.vertices()
            assert a == vv
            assert b == v
            ee = Edge.from_vertices(a, b)
            assert ee == e

if __name__ == "__main__":
    test_edge_vertex_isomorphism()