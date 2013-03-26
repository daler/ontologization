``ontologization``
==================

Wraps the command-line version of `Ontologizer <http://compbio.charite.de/contao/index.php/cmdlineOntologizer.html>`_ and does some stuff with the output.


* Downloads required files (``Ontologizer.jar``, ``.obo``,  annotation files
  for organism of choice, creates a lookup file)
* Runs Ontologizer
* Creates SVG and PNG plots of the output
* Reformats output to include GO names and descriptions
* Creates an interative HTML table of results (requires `entabled
  <https://github.com/daler/entabled>`_).
* Sends data to `REVIGO <http://revigo.irb.hr/>`_ server for interactive
  visualization (requires `requests
  <http://docs.python-requests.org/en/latest/)>`_).

Requires a list of genes of interest and a list of the population of genes to
consider.

Example usage
-------------

Setup
~~~~~

Get the code::

    $ git clone git://github.com/dalerr/ontologization.git

Install in develop mode::

    $ sudo python setup.py develop


Download data files needed for Ontologizer.  This includes an association file
(organism-dependent), an OBO file (organism-independent), and the
``Ontologizer.jar`` file itself.

By default, these files go in the source directory, so it should be writable.
The example uses genes from Drosophila, so download them.  This also makes
a JSON file containing a simple lookup table of GO ID to GO details::

    $ download_ontologization_files.py --organism dmelanogaster

Running
~~~~~~~
There are two example files, ``example_genes.txt`` and
``example_population.txt``.  Set up the object.  Results will be saved to the
directory ``ontologizer-example``::

    >>> from ontologization import Ontologizer, example_file
    >>> population = example_file('example_population.txt')
    >>> genes = example_file('example_genes.txt')
    >>> o = Ontologizer(
    ... genes=genes,
    ... population=population,
    ... mtc='Benjamini-Hochberg',
    ... organism='dmelanogaster',
    ... outdir='ontologizer-example')

Run Ontologizer::

    >>> o.ontologize()

Create PNG and SVG of the GO DAG, with different colors for each of the 3 root
GO ontologies, and more saturation indicating higher enrichment::

    >>> o.make_dot()

Add GO name and description to the output table::

    >>> o.reformat_table()


Create an interactive searchable/sortable/filterable HTML table and open it in
the browser (use ``show=False`` to disable this behavior)::

    >>> data_table_creator = o.entable()


Using an adjusted pval threshold of 0.1, send the list of genes and pvals to
REVIGO and open it in a web browser (use ``show=False`` to disable this
behavior).  All you should have to do is click the "Submit" button when the
REVIGO page loads.::

    >>> o.send_to_revigo(thresh=0.1)
