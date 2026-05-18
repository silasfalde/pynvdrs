def test_imports():
    import pynvdrs
    assert hasattr(pynvdrs, "paths")
    assert hasattr(pynvdrs, "umgpt")
