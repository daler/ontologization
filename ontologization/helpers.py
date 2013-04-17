import logging
import os
import inspect


def example_file(fn):
    """
    return example file
    """
    from files import DATA
    return os.path.join(DATA, fn)


def get_logger():
    """
    Return a logger named for the calling script with nice formatting
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(name)s] [%(asctime)s]: %(message)s')
    caller = whoami(offset=1)
    name = os.path.basename(caller)
    logger = logging.getLogger(name)
    return logger


def whoami(offset=0):
    """
    Returns the filename where this function was called.

    Increase `offset` to move up the stack.
    """
    return os.path.splitext(inspect.stack()[1 + offset][1])[0]

