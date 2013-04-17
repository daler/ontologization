#!/usr/bin/python

"""
Wraps standard Onologizer and formats output.
"""
import tempfile
import webbrowser
from collections import defaultdict
import requests
import simplejson
import os
import sys
import subprocess
import files
import helpers


logger = helpers.get_logger()


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
            raise ValueError("please provide either `organism` or "
                             "`association`, not both")

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
            '-n',
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
    def _annofile(self):
        return os.path.join(self.outdir, 'anno-' + self._name + '.txt')

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

    def _annotations_lookup(self):
        for_header = set()
        forward = {}
        for line in open(self._annofile):
            gene_id, _, terms_block = line.rstrip('\n\r').split('\t')
            forward[gene_id] = {}
            terms = terms_block.split()
            for t in terms:
                label, go_ids = t.split('=')
                for_header.update([label])
                go_ids = go_ids[1:-1].split(',')
                forward[gene_id][label] = go_ids
            reverse = defaultdict(lambda: defaultdict(list))
        for gene, go_ids_subdict in forward.iteritems():
            for label, go_ids in go_ids_subdict.items():
                for go_id in go_ids:
                    reverse[go_id][label].append(gene)

        return forward, reverse, list(for_header)

    def reformat_table(self, thresh=None):
        """
        Reformats table to include name and description (rather than just GO
        ID), and annotates each term with genes.  Result is in self.outdir, and
        has a .reformatted extension.

        If self.calcuation == 'MGSA' and `thresh` is not None, then only return
        terms with marginal posteriors > thresh.  If `thresh` is not None and
        self.calculation is something else, then only return lines < thresh.
        """
        if self.calculation == 'MGSA':
            p_col_label = 'marg'
        else:
            p_col_label = 'p.adjusted'

        # load json
        logger.info('Creating annotation lookups...')
        lookup = simplejson.load(open(files.FILES['lookup']))
        forward, reverse, for_header = self._annotations_lookup()
        fout = open(self._tablefile + '.reformatted', 'w')
        f = open(self._tablefile)
        header = f.readline().strip().split('\t')
        padj_field = header.index(p_col_label)
        header = ['name', 'definition'] + for_header + header

        fout.write('\t'.join(header) + '\n')
        lines = []
        for line in f:
            fields = line.strip().split('\t')
            if thresh is not None:
                if self.calculation == 'MGSA':
                    if float(fields[padj_field]) < thresh:
                        continue
                else:
                    if float(fields[padj_field]) > thresh:
                        continue
            genes_fields = []
            ID = fields[0]
            try:
                block = lookup[ID]
                name = ';'.join(block['name'])
                definition = ';'.join(block['def'])
            except KeyError:
                name = ""
                definition = ""

            genes_block = reverse[ID]
            genes_fields = []
            for label in for_header:
                try:
                    genes_fields.append(','.join(genes_block[label]))
                except KeyError:
                    genes_fields.append("")
            fields = [name, definition] + genes_fields + fields
            lines.append(fields)
        lines = sorted(lines, key=lambda x: float(x[len(genes_fields) + 2 + padj_field]))
        for line in lines:
            fout.write('\t'.join(line) + '\n')
        fout.close()
        logger.info('Wrote %s' % fout.name)

    def send_to_revigo(self, thresh=0.05, show=True):
        """
        Create a URL that can be sent to REVIGO for visualization.  Also
        creates a text file in the output dir that contains this url.

        If `show` is True (default), opens a web browser with that URL.
        """
        if self.calculation == 'MGSA':
            whatIsBetter = 'higher'
            isPValue = 'no'
            p_col_label = 'marg'
        else:
            whatIsBetter = 'lower'
            isPValue = 'yes'
            p_col_label = 'p.adjusted'

        f = open(self._tablefile)
        header = f.readline().strip().split('\t')
        ID_col = header.index('ID')
        p_col = header.index(p_col_label)
        results = []
        for line in f:
            fields = line.strip().split('\t')
            ID = fields[ID_col]
            pval = fields[p_col]
            if self.calculation == 'MGSA':
                if float(pval) > thresh:
                    results.append([ID, pval])
            else:
                if float(pval) < thresh:
                    results.append([ID, pval])

        if self.calculation == 'MGSA':
            reverse=True
        else:
            reverse=False
        results = sorted(results, key=lambda x: float(x[1]), reverse=reverse)

        limit = 100
        if len(results) > limit:
            logger.info(
                "Too many terms with padj < %s, truncating to top %s"
                % (thresh, limit))
            results = results[:limit]

        str_results = '\n'.join(['\t'.join(i) for i in results])
        payload = {
            'inputGoList': str_results,
            'isPValue': isPValue,
            'whatIsBetter': whatIsBetter,
            'outputListSize': 'medium',
            'goSizes': 'Drosophila melanogaster',
            'measure': "SIMREL",
        }
        r = requests.post('http://revigo.irb.hr/', params=payload)
        fout = open(
            os.path.join(
                self.outdir, self._name + '_revigo_thresh_%s' % thresh),
            'w'
        )
        fout.write(r.url + '\n')
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
        logger.info(
            'See %s for interactive table' % os.path.join(self.outdir, html))
        if show:
            webbrowser.open(os.path.join(self.outdir, html))
        return d


if __name__ == "__main__":
    o = Ontologizer(
        genes=helpers.example_file('example_genes.txt'),
        population=helpers.example_file('example_population.txt'),
        mtc='Benjamini-Hochberg',
        organism='dmelanogaster',
    )
    o.ontologize()
    o.reformat_table()
    #o.make_dot()
    o.send_to_revigo(thresh=0.1)
    d = o.entable()
