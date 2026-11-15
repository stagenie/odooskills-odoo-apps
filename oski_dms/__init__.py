from . import models
from . import wizards


def _oski_dms_post_init(env):
    """L'espace livré prend le nom de la langue de l'administrateur.

    ``name`` n'est pas traduisible (un espace est une donnée du client) : le
    XML le livre en anglais, et il est réécrit ici, à l'installation, dans la
    langue de ``base.user_admin``.
    """
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    workspace = env.ref("oski_dms.dms_workspace_general", raise_if_not_found=False)
    if admin and admin.lang and workspace:
        workspace.name = workspace.with_context(lang=admin.lang).env._("General")
