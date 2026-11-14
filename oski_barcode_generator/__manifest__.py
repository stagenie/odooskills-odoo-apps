{
    "name": "Bulk EAN13 Barcodes",
    "version": "20.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Assign valid EAN13 codes to every product that has none, in one go.",
    "description": """
Odoo can validate a barcode and compute its check digit; it cannot generate
one. A catalog of a thousand items without codes is therefore filled in by
hand, one product after another, with all the typos that implies.

This module assigns **valid EAN13 codes**, check digit included:

- from the product or variant list, on the selection;
- or on **all** products that have no code yet.

The default prefix starts with 2: the 20-29 range is the one the standard
reserves for a company's internal use. Departing from it would produce codes
resembling those of another manufacturer.

Products that already carry a code are **never** touched — overwriting a
code would break the printed labels and the scanners that read them. Numbers
already taken in the range are skipped, including those from an import.
""",
    "author": "OdooSkills",
    "website": "https://apps.odooskills.com",
    "support": "apps@odooskills.com",
    "license": "LGPL-3",
    "depends": ["product"],
    "images": [
        "static/description/screenshot_01_wizard.png",
        "static/description/screenshot_02_products.png",
    ],
    "data": [
        "security/ir.access.csv",
        "views/oski_barcode_generator_views.xml",
    ],
    "installable": True,
    "application": False,
}
