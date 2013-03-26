#!/usr/bin/python

"""
Wraps standard Onologizer and formats output.
"""
import tempfile
import webbrowser
import requests
import simplejson
import os
import sys
import subprocess
import files
import logging
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)
HERE = os.path.abspath(os.path.dirname(__file__))


class Ontologizer(object):
    def __init__(self, genes, population, path=files.FILES['ontologizer'],
                 association=None, go=files.FILES['go'],
                 calculation='Parent-Child-Union', dot=0.05,
                 mtc='Westfall-Young-Single-Step', resampling_steps=100,
                 outdir=None, organism=None):
        """
        genes:
                List of genes

        population:
            Population of genes

        path:
            Path to Ontologizer.jar

        association:
            Path to GO association file -- can provide "genome" instead.  Will
            download if needed.

        go:
            Path to GO ontology .obo file, will download if needed.

        calculation:
            Calculation to run, options are  MGSA, Parent-Child-Intersection,
            Parent-Child-Union (default), Term-For-Term, Topology-Elim,
            Topology-Weighted

        mtc:
            Multiple-testing correction.  Benjamini-Hochberg,
            Benjamini-Yekutieli, Bonferroni, Bonferroni-Holm, None,
            Westfall-Young-Single-Step (default), Westfall-Young-Step-Down

        resampling_steps:
            Number of resamplings

        dot:
            Create a .dot file for GraphViz, using this threshold and below

        organism:
            Organism to use
        """
        if organism and association:
            raise ValueError("please provide either `organism` or `association`,"
                             " not both")

        if outdir is None:
            outdir = 'ontologizer-output'
        self.outdir = outdir
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        self.path = path
        if association is None:
            try:
                association = files.FILES['association'][organism]
            except KeyError:
                raise ValueError('organism not supported; please specify the '
                                 'annotation file directly')
        self.association = association
        self.calculation = calculation
        self.go = go
        self.dot = dot
        self.mtc = mtc
        self.resampling_steps = resampling_steps
        self.genes = genes
        self.population = population

    def ontologize(self):
        """
        Run Ontologizer.jar using the parameters this instance was initialized
        with, saving results to self.outdir.
        """
        logfile = os.path.join(self.outdir, '.ontologizer.log')
        logger.info('See log at %s' % logfile)
        log = open(logfile, 'w')
        cmds = map(str, [
            'java',
            '-jar',
            self.path,
            '-a', self.association,
            '-g', self.go,
            '-s', self.genes,
            '-p', self.population,
            '-c', self.calculation,
            '-d', self.dot,
            '-m', self.mtc,
            '-r', self.resampling_steps,
            '--outdir', self.outdir
        ])

        logger.info(' '.join(cmds))
        p = subprocess.Popen(cmds, stderr=log, stdout=log)
        stdout, stderr = p.communicate()

    @property
    def _name(self):
        return '-'.join([
            os.path.splitext(os.path.basename(self.genes))[0],
            self.calculation,
            self.mtc])

    @property
    def _dotfile(self):
        return os.path.join(self.outdir, 'view-' + self._name + '.dot')

    @property
    def _tablefile(self):
        return os.path.join(self.outdir, 'table-' + self._name + '.txt')

    @property
    def _reformatted_tablefile(self):
        return self._tablefile + '.reformatted'

    def make_dot(self):
        """
        Write .png and .svg file to self.outdir.
        """
        logfile = os.path.join(self.outdir, '.dot.log')
        log = open(logfile, 'w')
        for ext in ['png', 'svg']:
            outfile = os.path.join(self.outdir, self._name + '_network.' + ext)
            cmds = [
                'dot',
                '-T', ext,
                self._dotfile,
                '-o', os.path.join(self.outdir, 'network.' + ext)]
            p = subprocess.Popen(cmds, stdout=log, stderr=log)
            stdout, stderr = p.communicate()
            if p.returncode:
                logger.info("ERROR in running `dot`; see %s" % logfile)
            logger.info('Wrote %s' % outfile)



    def reformat_table(self):
        """
        Reformats table to include name and description (rather than just GO
        ID).  Result is in self.outdir, and has a .reformatted extension.
        """
        # load json
        lookup = simplejson.load(open(files.FILES['lookup']))

        fout = open(self._tablefile + '.reformatted', 'w')
        f = open(self._tablefile)
        header = f.readline().strip().split('\t')
        header = ['name', 'definition'] + header
        fout.write('\t'.join(header) + '\n')
        for line in f:
            fields = line.strip().split('\t')
            ID = fields[0]
            try:
                block = lookup[ID]
                name = ';'.join(block['name'])
                definition = ';'.join(block['def'])
            except KeyError:
                name = ""
                definition = ""
            fields = [name, definition] + fields
            fout.write('\t'.join(fields) + '\n')
        fout.close()
        logger.info('Wrote %s' % fout.name)

    def send_to_revigo(self, thresh=0.05, show=True):
        """
        Create a URL that can be sent to REVIGO for visualization.  Also
        creates a text file in the output dir that contains this url.

        If `show` is True (default), opens a web browser with that URL.
        """
        f = open(self._tablefile)
        header = f.readline().strip().split('\t')
        ID_col = header.index('ID')
        p_col = header.index('p.adjusted')
        results = []
        for line in f:
            fields = line.strip().split('\t')
            ID = fields[ID_col]
            pval = fields[p_col]
            if float(pval) < thresh:
                results.append([ID, pval])

        str_results = '\n'.join(['\t'.join(i) for i in results])
        payload = {
            'inputGoList': str_results,
            'isPvalue': 'yes',
            'outputListSize': 'medium',
            'goSizes': 'Drosophila melanogaster',
            'measure': "SIMREL",
        }
        r = requests.post('http://revigo.irb.hr/', params=payload)
        fout = open(os.path.join(self.outdir, self._name + '_revigo_thresh_%s' % thresh), 'w')
        fout.write(r.url)
        fout.close()
        logger.info("Wrote %s" % fout.name)
        if show:
            webbrowser.open(r.url)

    def entable(self, show=True):
        """
        Creates an interative table of results; if `show` is True (default)
        then open it in a web browser.
        """
        import entabled
        css_fn = open(tempfile.NamedTemporaryFile(delete=False).name, 'w')
        css_fn.write("""
            .table td {
                     line-height: 105%;
                     }
                     """)
        css_fn.close()
        f = open(self._reformatted_tablefile)
        header = f.readline().replace('.', '_').strip().split('\t')
        data = []
        for line in f:
            data.append(line.strip('\n\r').replace('"', '').split('\t'))
        d = entabled.DataTableCreator(data=data, header=header,
                                      minmax=['p_adjusted'], title=self._name)
        html = 'interactive-%s.html' % self._name
        d.render(
            outdir=self.outdir,
            html=html,
            additional_css=css_fn.name,
        )
        logger.info('See %s for interactive table' % os.path.join(self.outdir, html))
        if show:
            webbrowser.open(os.path.join(self.outdir, html))
        return d


if __name__ == "__main__":
    o = Ontologizer(
        genes='example_genes.txt',
        population='example_population.txt',
        mtc='Benjamini-Hochberg',
        organism='dmelanogaster',
    )
    o.ontologize()
    o.make_dot()
    o.reformat_table()
    o.send_to_revigo(thresh=0.1)
    d = o.entable()
