import importlib.util
import os
import tempfile
import zipfile

import pytest

HERE = os.path.dirname(__file__)
_spec = importlib.util.spec_from_file_location(
    "build_zip", os.path.join(HERE, "build_zip.py")
)
build_zip = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_zip)


def _make_module(root, name):
    mod = os.path.join(root, name)
    os.makedirs(os.path.join(mod, "models"))
    with open(os.path.join(mod, "__manifest__.py"), "w") as f:
        f.write("{'name': '%s'}" % name)
    with open(os.path.join(mod, "models", "x.py"), "w") as f:
        f.write("# code")
    os.makedirs(os.path.join(mod, ".git"))
    with open(os.path.join(mod, ".git", "config"), "w") as f:
        f.write("secret")
    return mod


def test_build_zip_contains_module_with_prefix():
    with tempfile.TemporaryDirectory() as tmp:
        mod = _make_module(tmp, "oski_demo")
        out = os.path.join(tmp, "oski_demo.zip")
        build_zip.build_module_zip(mod, out)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert "oski_demo/__manifest__.py" in names
        assert "oski_demo/models/x.py" in names


def test_build_zip_excludes_git():
    with tempfile.TemporaryDirectory() as tmp:
        mod = _make_module(tmp, "oski_demo")
        out = os.path.join(tmp, "oski_demo.zip")
        build_zip.build_module_zip(mod, out)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert not any("/.git/" in n for n in names)


def test_build_zip_requires_manifest():
    with tempfile.TemporaryDirectory() as tmp:
        empty = os.path.join(tmp, "nomanifest")
        os.makedirs(empty)
        with pytest.raises(ValueError):
            build_zip.build_module_zip(empty, os.path.join(tmp, "x.zip"))
