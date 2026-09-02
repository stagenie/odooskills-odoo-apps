def activate_french(env, modules=("oski_app_store",)):
    """Active fr_FR sur le site de test et charge les fr.po des modules donnés."""
    fr = env["res.lang"]._activate_lang("fr_FR")
    website = env["website"].get_current_website()
    website.write({"language_ids": [(4, fr.id)]})
    env["ir.module.module"]._load_module_terms(list(modules), ["fr_FR"], overwrite=True)
    env.registry.clear_cache()
    return fr
