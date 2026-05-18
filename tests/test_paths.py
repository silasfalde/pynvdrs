from pynvdrs.paths import project_root, data_dir

def test_project_root():
    r = project_root()
    assert r is not None
