from copy import deepcopy as clone


def merge(root, *others):
    """Combine a bunch of dictionaries and return the result"""
    cp = clone(root)
    [cp.update(other) for other in others]
    return cp


def nested_get(d, *args, default=None):
    """Helper to access deeply-nested values in dictionaries"""
    for k in args:
        d = d.get(k)
        if not d:
            return default
    return d
