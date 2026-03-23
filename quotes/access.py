"""Reglas de visibilidad de cotizaciones por rol."""


def user_sees_only_own_quotes(user):
    """True si solo debe ver cotizaciones donde es vendedor (grupo Ventas).

    False (ve todas): superusuario, miembros del grupo Admin, o usuarios sin
    add/change en cotizaciones (p. ej. Solo_lectura).
    """
    if user.is_superuser:
        return False
    if user.groups.filter(name="Admin").exists():
        return False
    if user.has_perm("quotes.add_quote") or user.has_perm("quotes.change_quote"):
        return True
    return False
