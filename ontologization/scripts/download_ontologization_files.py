import os
from ontologization import files
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
    # OrderedDict for debugging the parser (make sure all blocks are parsed
    # with d.keys()[-1] and checking the file....
    d = collections.OrderedDict()
    for o in obo_parser(infile):
        d[o.id] = o
    fout = open(outfile, 'w')
    simplejson.dump(d, fout)
    fout.close()


def download_with_progress(name, url, dest):
    import progressbar
    import requests
    import math
    """
    Nice progress bar, but server needs to support Content-Length header, which
    some sites do not. So currently unused....
    """
    r = requests.get(url, stream=True)
    file_size = int(r.headers['content-length'])
    chunk_size = int(math.ceil(file_size / 100.))
    fout = open(dest, 'w')
    widgets = [
        '{0} ({1:.1f} MB): '.format(name, file_size / 1024. / 1024.),
        progressbar.Percentage(), ' ',
        progressbar.Bar(), ' ',
        progressbar.ETA(), ' ',
        progressbar.FileTransferSpeed()]
    pbar = progressbar.ProgressBar(
        widgets=widgets, maxval=file_size)
    pbar.start()
    for chunk in r.iter_content(chunk_size=chunk_size):
        fout.write(chunk)
        pbar.update(1)
    fout.close()
    pbar.finish()


def wget(url, dest, force=False):
    if os.path.exists(dest) and not force:
        print "%s exists; skipping." % dest
        return
    cmds = [
        'wget', '-O', dest, url]
    os.system(' '.join(cmds))


def download_jar(dest=None, force=False):
    source = files.ONTOLOGIZER_URL
    dest = dest or files.FILES['ontologizer']
    wget(source, dest, force=force)
    return dest


def download_associations(organism, dest=None, force=False):
    source = os.path.join(
        files.ASSOCIATIONS_URL,
        files.GENOME_ASSOCIATIONS[organism])
    dest = dest or files.FILES['association'][organism]
    wget(source + "?rev=HEAD", dest, force=force)
    return dest


def download_obo(dest=None, force=False):
    source = files.OBO_URL
    dest = dest or files.FILES['go']
    wget(source, dest, force=force)
    return dest


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument('--organism',
                    help='Organism (annotations file will be retrived for '
                    'this organism).  One of %s'
                    % files.GENOME_ASSOCIATIONS.keys())
    ap.add_argument('--file', help="Instead of --organism, you can specify "
                    "a filename from http://cvsweb.geneontology.org/cgi-bin"
                    "/cvsweb.cgi/go/gene-associations/ (e.g., gene_associat"
                    "ion.goa_rat.gz")
    args = ap.parse_args()
    if not args.organism and not args.file:
        ap.print_help()
        print "ERROR: --organism or --file required"
        sys.exit(1)

    jar_dest = download_jar()
    annot_dest = download_associations(args.organism)
    obo_dest = download_obo()
    obo_to_json(obo_dest, files.FILES['lookup'])
