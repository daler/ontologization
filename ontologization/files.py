import os

HERE = os.path.abspath(os.path.dirname(__file__))
DATA = os.path.join(HERE, 'data')

# Get the .jar file here.
ONTOLOGIZER_URL = ('http://compbio.charite.de/contao/index.php/cmdline'
                   'Ontologizer.html?file=tl_files/ontologizer/cmdline'
                   '/Ontologizer.jar')

# genome association files are at this dir
ASSOCIATIONS_URL = ('http://cvsweb.geneontology.org/cgi-bin/cvsweb.cgi/go/'
                    'gene-associations/')

# Specific genome associations
GENOME_ASSOCIATIONS = {
    'mmusculus': 'gene_association.goa_mouse.gz',
    'dmelanogaster': 'gene_association.fb.gz',
    'hsapiens': 'gene_association.goa_human.gz',
}

OBO_URL = 'http://www.geneontology.org/ontology/gene_ontology_edit.obo'

# Files to use for ontologizer.py
FILES = {
    'association': dict(
        [
            (k, os.path.join(DATA, v))
            for k, v in GENOME_ASSOCIATIONS.items()]),
    'go': os.path.join(DATA, 'gene_ontology_edit.obo'),
    'lookup': os.path.join(DATA, 'go_lookup.json'),
    'ontologizer': os.path.join(DATA, 'Ontologizer.jar'),
}
