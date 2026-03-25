def user_sees_only_own_quotes(user):
    if user.is_superuser:
        return False
    if user.groups.filter(name='Admin').exists():
        return False
    if user.has_perm('quotes.add_quote') or user.has_perm('quotes.change_quote'):
        return True
    return False
