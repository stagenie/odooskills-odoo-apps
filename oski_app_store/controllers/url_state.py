"""Construction pure de l'état d'URL du catalogue (facettes + tri).

Fonctions sans dépendance Odoo/HTTP : unit-testables isolément.
"""
from urllib.parse import urlencode


def toggle(values, value):
    """Ajoute `value` à la liste s'il est absent, le retire sinon.

    Retourne une nouvelle liste (n'altère pas l'entrée).
    """
    result = list(values)
    if value in result:
        result.remove(value)
    else:
        result.append(value)
    return result


def query_params(categories, tags, pricing, sort, search, version,
                 default_version="19.0"):
    """Paramètres de requête reflétant l'état de filtrage (dict, listes incluses).

    Omet les valeurs par défaut (pricing='all', sort='name', version=default,
    search vide, listes vides) pour des URLs propres. Sert aussi d'`url_args`
    au pager : chaque lien de page garde ainsi tous les filtres.
    """
    params = {}
    if categories:
        params["category"] = [str(c) for c in categories]
    if tags:
        params["tag"] = [str(t) for t in tags]
    if pricing and pricing != "all":
        params["pricing"] = pricing
    if sort and sort != "name":
        params["sort"] = sort
    if search:
        params["search"] = search
    if version and version != default_version:
        params["v"] = version
    return params


def build_query(categories, tags, pricing, sort, search, version,
                default_version="19.0", path="/apps"):
    """Construit l'URL `/apps` reflétant l'état de filtrage, querystring encodée.

    Un changement de filtre renvoie toujours en page 1 (`path` par défaut).
    """
    params = query_params(categories, tags, pricing, sort, search, version,
                          default_version)
    if not params:
        return path
    return path + "?" + urlencode(params, doseq=True)
