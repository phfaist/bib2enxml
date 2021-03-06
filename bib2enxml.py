
# Filter to save an old EndNote XML copy of the bibtex database.

from __future__ import unicode_literals, print_function

import os
import os.path
import re
import codecs
import unicodedata
import string
import textwrap
from datetime import datetime
import logging

from pybtex.database import BibliographyData, Entry

try:
    # bibolamazi v3
    from bibolamazi.core.bibfilter import BibFilter, BibFilterError
    from bibolamazi.core.butils import getbool
    from bibolamazi.filters.util import arxivutil
    from pylatexenc import latex2text
    logger = logging.getLogger(__name__)
except ImportError:
    # bibolamazi v2
    from core.bibfilter import BibFilter, BibFilterError
    from core.butils import getbool
    from core.blogger import logger
    from core.pylatexenc import latex2text
    from filters.util import arxivutil

    

# --------------------------------------------------


def unicode_to_xml(u):
    return re.sub(r'[^-a-zA-Z0-9 \t\n\+/\.,;:\!\@\#\$\%\^\*()_{}\[\]|?=]',
                  lambda m: '&#x%x;'%(ord(m.group())),
                  unicode(u),
                  flags=re.UNICODE).encode('latin1')

def delatex_for_xml(s):
    s = unicode(s)
    logger.longdebug('delatexing `%s\' [:100] ...', s[:100])
    text = latex2text.latex2text(s, tolerant_parsing=True, keep_comments=True)
    #logger.longdebug('  --> text is %r [:100]', text[:100])
    xml = unicode_to_xml(text)
    logger.longdebug('  --> xml is `%s\' [:100]', xml[:100])
    return xml


# --------------------------------------------------

ENT_BOOK = 6
ENT_BOOK_SECTION = 5
ENT_CONFERENCE_PROCEEDINGS = 10
ENT_GENERIC = 13
ENT_JOURNAL_ARTICLE = 17
ENT_ONLINE_DATABASE = 45
ENT_REPORT = 10
ENT_THESIS = 32
ENT_UNPUBLISHED_WORK = 34

ENTYPES = {
    ENT_BOOK : "Book",
    ENT_BOOK_SECTION : "Book Section",
    ENT_CONFERENCE_PROCEEDINGS : "Conference Proceedings",
    ENT_GENERIC : "Generic",
    ENT_JOURNAL_ARTICLE : "Journal Article",
    ENT_ONLINE_DATABASE : "Online Database",
    ENT_REPORT : "Report",
    ENT_THESIS : "Thesis",
    ENT_UNPUBLISHED_WORK : "Unpublished Work",
    }



# --------------------------------------------------

HELP_AUTHOR = u"""\
Bib2EnXml filter by Philippe Faist, ETHZ, (C) 2014, GPL 3+
"""

HELP_DESC = u"""\
Filter that saves a copy of the current bibolamazi bibtex database as old EndNote XML format
"""

HELP_TEXT = u"""

Write me.....

"""


class Bib2EnXmlFilter(BibFilter):

    helpauthor = HELP_AUTHOR
    helpdescription = HELP_DESC
    helptext = HELP_TEXT


    def __init__(self, xmlfile="publications_%Y-%m-%dT%H-%M-%S.xml", export_annote=True,
                 no_arxiv_urls=False, fixes_for_ethz=False, print_diff_to_last=False):
        """
        Bib2EnXmlFilter constructor.

        Arguments:

         - xmlfile: The name of the XML file to output to. This string will be parsed with
           `strftime()`, see [https://docs.python.org/2/library/time.html#time.strftime].
           If the file exists, it will not be overwritten and an error will be reported.
           The default value is 'publications_%Y-%m-%dT%H-%M-%S.xml'.

         - export_annote(bool): If set to `False`, then annote={} fields in the bibtex
           will not be exported into <notes>, as when this is set to `True` (`True` is the
           default).

         - no_arxiv_urls(bool): If set to `True`, then arxiv URLs will automatically be
           added to the entry. Note that this is the only way to link to the online arXiv
           version, but you may disable this option if the URL is already present in the
           entry.

         - fixes_for_ethz(bool): If set to `True`, includes some fixes & changes to prepare
           for proper upload on ETHZ Silva's CMS publication database.

         - print_diff_to_last(bool): If `True`, then print out the difference between the
           new outputted XML file and the latest file generated with the same pattern.
        """

        BibFilter.__init__(self);

        self.xmlfilepattern = xmlfile
        self.xmlfile = datetime.now().strftime(xmlfile)
        self.export_annote = getbool(export_annote)
        self.no_arxiv_urls = getbool(no_arxiv_urls)
        self.fixes_for_ethz = getbool(fixes_for_ethz)
        self.print_diff_to_last = getbool(print_diff_to_last)

        logger.debug('bib2enxml: xmlfile=%r', self.xmlfile)


    def getRunningMessage(self):
        return u"Saving a copy of the database to `%s' in old EndNote XML format" %(self.xmlfile)
    

    def action(self):
        return BibFilter.BIB_FILTER_BIBOLAMAZIFILE;


    def requested_cache_accessors(self):
        return [
            arxivutil.ArxivInfoCacheAccessor,
            arxivutil.ArxivFetchedAPIInfoCacheAccessor
            ]

    def export_entry_xml(self, fobj, recnumber, entry, arxivaccess):
        """
        Writes the XML code representing a record ('<record>...</record>') for the given
        entry in the open file pointed by `fobj` (a file-like object).

        Arguments:

          - `fobj`: a file-like object to write the XML record to

          - `recnumber` is the number of the record (a simple counter increasing by one
            for each record)
          
          - `entry` is a pybtex.database.Entry object.

          - `arxivaccess`: an access to the arXiv information cache. This should be
            obtained with `arxivutil.setup_and_get_arxiv_accessor()`.
        """

        arxivinfo = arxivaccess.getArXivInfo(entry.key)
        archiveprefix = ((arxivinfo['archiveprefix'] or "arxiv").lower() if arxivinfo else None)

        logger.longdebug("Writing entry %s, arxivinfo=%r", entry.key, arxivinfo)

        # this will be where we collect the XML entries to set. Dictionary keys are XML
        # tags. Can be recursive. Lists are joined together into a string with newlines.
        xmlfields = {
            'titles': { },
            'urls': { 'related-urls': [] },
            'notes': [],
            'dates': { 'pub-dates': { } },
            }
        

        # start the record.
        # -----------------
        
        fobj.write("<record>"
                   "<database name=\"publications.enl\" path=\"/dummy/path/to/publications.enl\">"
                       "publications.enl"
                   "</database>"
                   "<source-app name=\"EndNote\" version=\"12.0\">EndNote</source-app>")

        fobj.write( ("<rec-number>%(recnumber)d</rec-number>"
                     "<foreign-keys>"
                       "<key app=\"EN\" db-id=\"fzs9rzp9rzp5dfeds5xpfdtow5vz9eref2d5\">%(recnumber)d</key>"
                     "</foreign-keys>"
                     ) % {'recnumber':recnumber}
                    )

        # now, set the entry type.
        # ------------------------
        
        entype = None
        if (arxivinfo is not None and not arxivinfo['published']
            and entry.type in (u'article', u'unpublished', u'misc',)):
            entype = ENT_ONLINE_DATABASE
        elif (entry.type == 'article'):
            entype = ENT_JOURNAL_ARTICLE
        elif entry.type == 'proceedings' or entry.type == 'inproceedings' or entry.type == 'conference':
            entype = ENT_CONFERENCE_PROCEEDINGS
        elif entry.type == 'phdthesis':
            entype = ENT_THESIS
            xmlfields['work-type'] = "PhD Thesis"
        elif entry.type == 'book':
            entype = ENT_BOOK
        elif entry.type == 'inbook' or entry.type == 'incollection':
            entype = ENT_BOOK_SECTION
        elif entry.type == 'mastersthesis':
            entype = ENT_THESIS
            xmlfields['work-type'] = "Master's Thesis"
        elif entry.type == 'misc':
            entype = ENT_GENERIC
        elif entry.type == 'unpublished':
            entype = ENT_UNPUBLISHED_WORK
        elif entry.type == 'techreport':
            entype = ENT_REPORT
        else:
            logger.warning("Unknown entry type: %s, setting `Generic'", entry.type)
            entype = ENT_GENERIC

        fobj.write("<ref-type name=\"%s\">%d</ref-type>" %(ENTYPES.get(entype), entype))

        # write the authors & editors:
        # ----------------------------
        
        def writeperson(person):
            fobj.write("<author>" +
                         "<style face=\"normal\" font=\"default\" size=\"100%\">" +
                           (
                           delatex_for_xml(unicode(person))
                           ) +
                         "</style>" +
                       "</author>")

        fobj.write("<contributors>")

        # authors
        fobj.write("<authors>")

        for author in entry.persons.get('author',[]):
            writeperson(author)

        fobj.write("</authors>")

        # editors
        editors = entry.persons.get('editor',[])
        if len(editors):
            fobj.write("<secondary-authors>")
            
            for editor in editors:
                writeperson(editor)
            
            fobj.write("</secondary-authors>")

        fobj.write("</contributors>")

        # and now, prepare the rest of the XML fields.
        # --------------------------------------------

        for fldname, fldvalue in entry.fields.items():
            
            fldname = fldname.lower()
            value = delatex_for_xml(fldvalue)
            
            if fldname == 'address':
                xmlfields['pub-location'] = value
            elif fldname == 'annote':
                if self.export_annote:
                    xmlfields['notes'].append(value)
            elif fldname == 'booktitle':
                xmlfields['titles']['secondary-title'] = value
            elif fldname == 'chapter':
                xmlfields['section'] = value
            elif fldname == 'crossref':
                logger.warning("XML Export: Ignoring cross-ref in entry %s!", entry.key)
                continue
            elif fldname == 'edition':
                xmlfields['edition'] = value
            elif fldname == 'eprint':
                if arxivinfo is None or archiveprefix != 'arxiv':
                    xmlfields['notes'].append(value)
                # otherwise, we'll set up the arXiv information correctly anyway.
            elif fldname == 'journal':
                if (self.fixes_for_ethz and arxivinfo and not arxivinfo['published']
                    and 'arxiv' in fldvalue.lower()):
                    # unpublished, will be treated anyway automatically
                    pass
                else:
                    xmlfields['titles']['secondary-title'] = value
            elif fldname == 'key':
                logger.debug("Ignoring `key={%s}' field in %s for XML export", value, entry.key)
            elif fldname == 'language':
                xmlfields['language'] = value
            elif fldname == 'month':
                if not self.fixes_for_ethz:
                    xmlfields['dates']['pub-dates'].setdefault('date','')
                    xmlfields['dates']['pub-dates']['date'] += value
            elif fldname == 'note':
                xmlfields['notes'].append(value)
            elif fldname == 'number':
                xmlfields['number'] = value
            elif fldname == 'pages':
                xmlfields['pages'] = value
            elif fldname == 'publisher':
                xmlfields['publisher'] = value
            elif fldname == 'series':
                xmlfields['titles']['secondary-title'] = value
            elif fldname == 'title':
                xmlfields['titles']['title'] = value
            elif fldname == 'type':
                xmlfields['work-type'] = value
            elif fldname == 'url':
                for url in value.split():
                    logger.longdebug("Adding URL %s", url)
                    xmlfields['urls']['related-urls'].append({'url': url})
            elif fldname == 'volume':
                xmlfields['volume'] = value
            elif fldname == 'year':
                xmlfields['dates']['year'] = value
            elif fldname == 'abstract':
                xmlfields['abstract'] = value
            elif fldname == 'archiveprefix':
                if not archiveprefix and value:
                    xmlfields['notes'].append(value)
            elif fldname == 'arxivid':
                pass # skip, we have all we need in arxivinfo
            elif fldname == 'primaryclass':
                pass # skip, we have all we need in arxivinfo
            elif fldname == 'keywords' or fldname == 'mendeley-tags':
                if self.fixes_for_ethz:
                    pass
                else:
                    xmlfields.setdefault('keywords', [])
                    for kw in re.split(r'[,;]+', fldvalue):
                        kwval = delatex_for_xml(kw.strip())
                        logger.longdebug("kw=%r, kwval=%r", kw, kwval)
                        if kwval not in ( x['keyword'] for x in xmlfields['keywords'] ):
                            xmlfields['keywords'].append({'keyword': kwval})
            elif fldname == 'doi':
                if not self.fixes_for_ethz:
                    xmlfields['electronic-resource-num'] = value
            elif fldname == 'issn' or fldname == 'isbn':
                if not self.fixes_for_ethz:
                    xmlfields['isbn'] = value
            elif fldname == 'school':
                if 'publisher' in entry.fields:
                    xmlfields['titles']['secondary-title'] = value
                else:
                    xmlfields['publisher'] = value
            elif (fldname == 'howpublished' or fldname == 'institution' or
                  fldname == 'organization'):
                xmlfields['notes'].append(value)
            elif (fldname == 'pmid' or fldname == 'shorttitle'):
                pass # don't really care
            else:
                logger.warning(u"%s: Ignoring unknown bibtex field %s=%r", entry.key, fldname, fldvalue)


        # set the arXiv preprint information
        # ----------------------------------

        if arxivinfo is not None:
            if archiveprefix == 'arxiv':
                # it's on the arXiv
                if self.fixes_for_ethz and (arxivinfo['published'] or
                                            entry.type in (u'phdthesis', u'mastersthesis',)):
                    pass
                else:
                    xmlfields['remote-database-name'] = "arXiv.org"
                if not self.no_arxiv_urls:
                    xmlfields['urls']['related-urls'].append( {
                        'url': "http://arxiv.org/abs/" + str(arxivinfo['arxivid'])
                        } )
            else:
                # it's another e-print, not too sure... the user must have provieded an
                # URL or e-print which will be set in a URL or <notes>
                xmlfields['remote-database-name'] = archiveprefix

        # Now, write those remaining XML fields and wrap up.
        # --------------------------------------------------

        def write_xmlfields(val):

            if isinstance(val, dict):
                for k,v in val.items():
                    if not v:
                        fobj.write("<"+k+"/>")
                    else:
                        fobj.write("<"+k+">")
                        write_xmlfields(v)
                        fobj.write("</"+k+">")
                return

            if isinstance(val, list):
                if all( (isinstance(x,basestring) for x in val) ):
                    write_xmlfields("\n".join(val))
                else:
                    for v in val:
                        write_xmlfields(v)
                return
            
            # remember that v was already de-latex'ed and utf-8 encoded
            fobj.write("<style face=\"normal\" font=\"normal\" size=\"100%\">"
                       + val + "</style>")
            return

        write_xmlfields(xmlfields)
        
        fobj.write("</record>")
                
        return
        

    def filter_bibolamazifile(self, bibolamazifile):
        #
        # bibdata is a pybtex.database.BibliographyData object
        #

        bibdata = bibolamazifile.bibliographyData();

        arxivaccess = arxivutil.setup_and_get_arxiv_accessor(bibolamazifile)

        if (os.path.exists(self.xmlfile)):
            raise BibFilterError(self.name(), "File %s exists, won't overwrite." %(self.xmlfile));

        xmlfilepath = bibolamazifile.resolveSourcePath(self.xmlfile)

        with open(xmlfilepath, 'w') as fobj:

            fobj.write("<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"
                       "<xml><records>")

            recnumber = 1;
            for key, entry in bibolamazifile.bibliographyData().entries.items():
                fobj.write("\n") #makes debugging easier, text editors hate very long lines...
                # export & write this entry
                self.export_entry_xml(fobj, recnumber, entry, arxivaccess)
                recnumber += 1

            fobj.write("</records></xml>");

        if self.print_diff_to_last:
            # first, find the latest file which has our given pattern. Use strptime to
            # parse the date/time
            (dn,bn) = os.path.split(os.path.abspath(bibolamazifile.resolveSourcePath(self.xmlfilepattern)))
            def strptimeornone(fn):
                try:
                    return datetime.strptime(fn, bn)
                except ValueError:
                    return None

            files_with_dt = [
                pair for pair in (
                    (fn, strptimeornone(fn)) for fn in os.listdir(dn)
                    )
                if pair[1] is not None and pair[0] != os.path.basename(self.xmlfile)
                ]

            logger.longdebug("bib2enxml: preparing diff: got file list %r", files_with_dt)

            if not files_with_dt:
                # no file to display diff with
                logger.info("bib2enxml: No other file with same pattern to display diff with.")
            else:

                fn = (max(files_with_dt, key=lambda pair: pair[1]))[0]

                import diffendnoteex2xml

                # now display diff
                width = 100
                difftext = diffendnoteex2xml.getFormattedDiffContents(
                    os.path.join(dn,fn),
                    xmlfilepath,
                    txtwid=width,
                    addindent=2,
                    )
                logger.info("#"*width + "\n" +
                            "DIFFERENCES:  %s  vs  %s\n"%(fn, self.xmlfile) +
                            "#"*width + "\n" +
                            (difftext if difftext else "(no differences)\n") + "#"*width)


        return


def bibolamazi_filter_class():
    return Bib2EnXmlFilter;

