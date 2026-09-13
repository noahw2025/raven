from app.vector_layout import cluster_vectors


def test_semantic_clusters_do_not_chain_unrelated_neighborhoods():
    rows=[
        {"id":"music-1","vector":[1.0,0.05,0.0]},
        {"id":"music-2","vector":[0.98,0.12,0.0]},
        {"id":"career-1","vector":[0.02,1.0,0.0]},
        {"id":"career-2","vector":[0.08,0.99,0.0]},
        {"id":"research-1","vector":[0.0,0.02,1.0]},
        {"id":"research-2","vector":[0.0,0.1,0.99]},
    ]
    clusters,sizes,cohesion=cluster_vectors(rows)
    assert clusters["music-1"]==clusters["music-2"]
    assert clusters["career-1"]==clusters["career-2"]
    assert clusters["research-1"]==clusters["research-2"]
    assert len({clusters["music-1"],clusters["career-1"],clusters["research-1"]})==3
    assert all(size==2 for size in sizes.values())
    assert min(cohesion.values())>.98
