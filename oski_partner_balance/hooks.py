def post_init_hook(env):
    """Align the operation datetime of existing moves on their creation time.

    Odoo fills a newly added column with the field default, which means every
    pre-existing move would otherwise share the *same* installation timestamp
    and no chronological order could be derived from it. The UPDATE is
    therefore unconditional: filtering on NULL would match nothing.
    """
    env.cr.execute("UPDATE account_move SET oski_operation_datetime = create_date")
