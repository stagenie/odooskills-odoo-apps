def migrate(cr, version):
    """Supprime les ir.model.fields.selection de l'ancien champ Selection odoo_version.

    Sans cela, le nettoyage ir.model.data en fin de chargement tente
    d'accéder à field.ondelete (attribut Selection) sur le nouveau champ
    Char related, provoquant un AttributeError fatal.

    L'ORM v19 stocke les valeurs de sélection dans ir_model_fields_selection
    (et leur entrée ir.model.data correspondante dans ir_model_data).
    """
    # Supprimer d'abord les entrées ir.model.data qui pointent vers ces sélections,
    # pour éviter que _process_end ne tente de les unlink via ORM.
    cr.execute(
        """
        DELETE FROM ir_model_data imd
        USING ir_model_fields_selection imfs
        JOIN ir_model_fields imf ON imfs.field_id = imf.id
        WHERE imd.model = 'ir.model.fields.selection'
          AND imd.res_id = imfs.id
          AND imf.model = 'oski.module.version'
          AND imf.name = 'odoo_version'
        """
    )
    # Supprimer ensuite les sélections elles-mêmes.
    cr.execute(
        """
        DELETE FROM ir_model_fields_selection imfs
        USING ir_model_fields imf
        WHERE imfs.field_id = imf.id
          AND imf.model = 'oski.module.version'
          AND imf.name = 'odoo_version'
        """
    )
