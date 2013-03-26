#!/usr/bin/python

"""
Convert an .obo file into a JSON dictionary of items.
"""
import simplejson
import collections
import sys


class OBO(collections.defaultdict):
    def __init__(self, block, *args, **kwargs):
        super(OBO, self).__init__(list, *args, **kwargs)
        self._block = block
        for line in block:
            key, val = line.split(':', 1)
            val = val.strip()
            self[key].append(val)
            setattr(self, key, val)

    def __repr__(self):
        return "<OBO instance [%s]>" % self.id

    def __str__(self):
        return '\n'.join(self._block)


def obo_parser(f):
    """
    yields blocks from an .obo file
    """
    f = open(f)

    # Ignore header
    while True:
        line = f.readline()
        if line.startswith('[Term]'):
            break

    block = []
    for line in f:

        # we've hit the bottom of the file
        if line.startswith('[Typedef]'):
            yield OBO(block)
            raise StopIteration

        if line.startswith('[Term]'):
            yield OBO(block)
            block = []
        else:
            if line.strip():
                block.append(line.strip())


def obo_to_json(infile, outfile):
    # OrderedDict for debugging the parser (make sure all blocks are parsed with
    # d.keys()[-1] and checking the file....
    d = collections.OrderedDict()
    for o in obo_parser(infile):
        d[o.id] = o
    fout = open(outfile, 'w')
    simplejson.dump(d, fout)
    fout.close()
