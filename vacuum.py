
# Filter to remove all entries from the database.

from __future__ import unicode_literals, print_function

from pybtex.database import BibliographyData, Entry

import logging


try:
    # bibolamazi v3
    from bibolamazi.core.bibfilter import BibFilter, BibFilterError
    from pylatexenc import latex2text
    logger = logging.getLogger(__name__)
except ImportError:
    # bibolamazi v2
    from core.bibfilter import BibFilter, BibFilterError
    from core.blogger import logger
    from core.pylatexenc import latex2text



# --------------------------------------------------

HELP_AUTHOR = u"""\
vacuum filter by Philippe Faist, ETHZ, (C) 2014, GPL 3+
"""

HELP_DESC = u"""\
Filter that removes all entries from the database. Only useful in conjunction with and
after, e.g., bib2enxml filter.
"""

HELP_TEXT = u"""
Very simple. Leaves no database entry behind. Saves space in the bibolamazi file. Very
clean.
"""


class VacuumFilter(BibFilter):

    helpauthor = HELP_AUTHOR
    helpdescription = HELP_DESC
    helptext = HELP_TEXT

    def __init__(self):
        """
        Vacuum filter constructor.
        """

        BibFilter.__init__(self);


    def name(self):
        return "vacuum"

    def getRunningMessage(self):
        return u"Vacuuming all entries"

    def action(self):
        return BibFilter.BIB_FILTER_BIBOLAMAZIFILE;


    def filter_bibolamazifile(self, bibolamazifile):
        #
        # bibdata is a pybtex.database.BibliographyData object
        #

        bibdata = BibliographyData()

        bibolamazifile.setBibliographyData(bibdata)

        return


def bibolamazi_filter_class():
    return VacuumFilter;

