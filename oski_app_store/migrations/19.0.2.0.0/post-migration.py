def migrate(cr, version):
    """Mappe l'ancienne Selection odoo_version vers oski.odoo.version."""
    cr.execute(
        """
        UPDATE oski_module_version mv
        SET odoo_version_id = ov.id
        FROM oski_odoo_version ov
        WHERE mv.odoo_version_id IS NULL
          AND mv.odoo_version = ov.name
        """
    )
