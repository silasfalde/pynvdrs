def test_imports():
    import pynvdrs

    assert hasattr(pynvdrs, "paths")
    assert hasattr(pynvdrs, "umgpt")
    assert hasattr(pynvdrs, "text")
    assert hasattr(pynvdrs, "annotation")
    assert hasattr(pynvdrs, "demographics")
    assert pynvdrs.__version__
