import os
import tempfile
import zipfile

from odoo.tests import TransactionCase, tagged

from odoo.addons.oski_app_store.tools.build_zip import build_module_zip


@tagged("post_install", "-at_install")
class TestBuildZip(TransactionCase):
    def test_zip_includes_description_assets(self):
        """L'archive embarque static/description complet (compat apps.odoo.com)."""
        with tempfile.TemporaryDirectory() as tmp:
            mod = os.path.join(tmp, "oski_fake")
            desc = os.path.join(mod, "static", "description")
            os.makedirs(desc)
            with open(os.path.join(mod, "__manifest__.py"), "w") as f:
                f.write("{}")
            with open(os.path.join(desc, "index.html"), "w") as f:
                f.write("<section/>")
            with open(os.path.join(desc, "screenshot_01.png"), "wb") as f:
                f.write(b"png")
            out = os.path.join(tmp, "out.zip")
            build_module_zip(mod, out)
            names = zipfile.ZipFile(out).namelist()
            self.assertIn("oski_fake/static/description/index.html", names)
            self.assertIn("oski_fake/static/description/screenshot_01.png", names)
