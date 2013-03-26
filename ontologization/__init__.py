import os
from ontologize import Ontologizer


def example_file(fn):
    """
    return example file
    """
    from files import DATA
    return os.path.join(DATA, fn)

