
import sys
import argparse
import textwrap
import pydoc
import copy
import difflib
import locale
import xml.etree.ElementTree as ET



# --------------------------------------------------------

def attrof(elem, att, default=''):
    if elem is None:
        return default
    return elem.attrib.get(att, default)

def contentof(elem, default=''):
    if elem is None:
        return default
    alltxt = u''
    for txt in elem.itertext():
        alltxt += txt
    return alltxt

def find_and_iter(elem, subtag, itertag):
    t = elem.find(subtag)
    if t is None:
        return
    for z in t.iter(itertag):
        yield z

def fmtelem(elem, **kwargs):
    txtwid = kwargs.get('txtwid', 80)
    addindent = kwargs.get('addindent', 4)
    flattenlevels = kwargs.get('flattenlevels', [])
    skip = kwargs.get('skip', [])
    keysepstr = kwargs.get('keysepstr', u': ')
    keycolmultof = kwargs.get('keycolmultof', 1)
    
    k2 = copy.deepcopy(kwargs)
    k2['txtwid'] = txtwid-addindent
    
    #if elem.tag in skip:
    #    return "".join([fmtelem(einner, **k2) for einner in e])

    textcontent = u''
    
    if len(elem) == 0:
        t = elem.text
        if t:
            textcontent += textwrap.fill(elem.text, width=txtwid)

    d = {}
    for e in elem:
        if e.tag in skip:
            continue

        if e.tag in flattenlevels:
            textcontent += fmtelem(e, **kwargs) # our own kwargs
            continue

        val = fmtelem(e, **k2)

        dkey = e.tag
        if e.keys():
            dkey += "[" +  ",".join(["%s=%s"%(kk,vv) for (kk,vv) in sorted(e.items())])  + "]"

        if dkey in d:
            d[dkey].append(val)
        else:
            d[dkey] = [ val ]

    def fmtline(key, val):

        # how many columns the key needs
        lenkeysep = len(key)+len(keysepstr);
        keywid = int((lenkeysep) / keycolmultof) * keycolmultof
        if lenkeysep % keycolmultof != 0:
            keywid += keycolmultof
            
        if '\n' in val or keywid + len(val) > txtwid:
            return key + keysepstr + "\n" + (" "*addindent) + val.replace("\n", "\n"+(" "*addindent))
        return key + keysepstr + " "*(keywid-lenkeysep) + val

    txtlines = []
    for k in sorted(d.keys()):
        v = d[k]
        if len(v) > 1:
            for n in range(len(v)):
                txtlines.append(fmtline('%s(%02d)'%(k,n), v[n]))
        else:
            txtlines.append(fmtline(k, v[0]))

    return textcontent + "\n".join(txtlines)


class ParsedXMLEndNoteX2:
    def __init__(self, fname):
        self.tree = ET.parse(fname)
        self.root = self.tree.getroot()
        self.records = self.root.find('records')
        if self.records is None:
            raise ValueError("XML file `%s' does not have a <records> root element"%(fname))
     
    def rec_iter(self):
        for elem in self.records:
            if elem.tag != 'record':
                continue
            yield ParsedXMLEndNoteX2.Record(elem)

    class Record:
        def __init__(self, elem):
            self.elem = elem

        def sortkey(self):
            return self.fmt()

        def fmt(self, **kwargs):
            return fmtelem(self.elem, **kwargs)
        
#             reftype = attrof(self.elem.find('ref-type'), 'name', default='<unknown>')
#             txt = u"[" + reftype + "] "

#             contr = self.elem.find('contributors')
#             if contr is not None:
#                 authtxts = []
#                 authtxts2 = []
#                 authtxts3 = []
#                 for auth in find_and_iter(contr, 'authors', 'author'):
#                     authtxts.append(contentof(auth))
#                 for auth in find_and_iter(contr, 'secondary_authors', 'secondary_author'):
#                     authtxts2.append(contentof(auth))
#                 for auth in find_and_iter(contr, 'tertiary_authors', 'tertiary_author'):
#                     authtxts3.append(contentof(auth))

#                 txt = (txt + "; ".join(authtxts) + "\n")
#                 if authtxts2:
#                     txt += ("Secondary Authors: " + "; ".join(authtxts2) + "\n")
#                 if authtxts3:
#                     txt += ("Tertiary Authors: " + "; ".join(authtxts3) + "\n")

#             else:
#                 txt += "(no authors)\n"

#             txt += ("TITLE: " + contentof(self.elem.find('title')) + "\n")
#             title2 = self.elem.find('secondary_title')
#             if title2:
#                 txt += ("SEC. TITLE: " + contentof(title2) + "\n")
#             title3 = self.elem.find('tertiary_title')
#             if title3:
#                 txt += ("TER. TITLE: " + contentof(title3) + '\n')

#             txt += "Dates: " + contentof(self.elem.find('dates')) + "\n"

#             txt += "Publisher: " + contentof(self.elem.find('publisher')) + "\n"

#             txt += 

#             wrapper = textwrap.TextWrapper(width=txtwid)


# -----------------------------------------------------------------------


# from http://stackoverflow.com/a/566752/1694896

def getTerminalSize():
    import os
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
        '1234'))
        except:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

        ### Use get(key[, default]) instead of a try/catch
        #try:
        #    cr = (env['LINES'], env['COLUMNS'])
        #except:
        #    cr = (25, 80)
    return int(cr[1]), int(cr[0])



def getFormattedFileContents(fname, LISTSEP=None, sortedentries=False, **kwargs):

    fmtkwargs = {
        'skip': ['database', 'source-app', 'foreign-keys', 'rec-number'],
        'flattenlevels': ['style']
        }

    if 'txtwid' not in kwargs or not kwargs['txtwid']:
        try:
            (termwid, termhgt) = getTerminalSize()
        except Exception as e:
            print "Can't determine console width, defaulting to 80: %s"%(e)
            termwid = 80
            termhgt = None
    else:
        termwid = kwargs['txtwid']
    txtwid = termwid
        
    afileobj = ParsedXMLEndNoteX2(fname)

    # just display entries in fname

    if not LISTSEP:
        LISTSEP = "\n\n" + ("-"*termwid) + "\n\n"

    fmtkwargs.update(kwargs)
    fmtkwargs['txtwid'] = txtwid

    items = [rec.fmt(**fmtkwargs) for rec in afileobj.rec_iter()]

    if sortedentries:
        items = sorted(items)

    return LISTSEP.join(items)


def getFormattedDiffContents(afname, bfname, RECSEP=None, sortedentries=True, txtwid=None, **kwargs):
    #
    # display DIFF of two XML files
    #

    fmtkwargs = {
        'skip': ['database', 'source-app', 'foreign-keys', 'rec-number'],
        'flattenlevels': ['style']
        }
    if txtwid is None:
        try:
            (termwid, termhgt) = getTerminalSize()
        except Exception as e:
            print "Can't determine console width, defaulting to 80: %s"%(e)
            termwid = 80
            termhgt = None
    else:
        termwid = txtwid

    afileobj = ParsedXMLEndNoteX2(afname)
    bfileobj = ParsedXMLEndNoteX2(bfname)

    txtwidwrap = int(termwid*0.45)
    txtwid = int(termwid*0.5)

    fmtkwargs.update(kwargs)
    fmtkwargs['txtwid'] = txtwidwrap

    alist = [ rec.fmt(**fmtkwargs) for rec in afileobj.rec_iter() ]
    blist = [ rec.fmt(**fmtkwargs) for rec in bfileobj.rec_iter() ]

    if sortedentries:
        alist = sorted(alist)
        blist = sorted(blist)

    seqm = difflib.SequenceMatcher(isjunk=None, a=alist, b=blist, autojunk=False)

    data = ''

    def getcompareitemlines(left, right, leftwid, rightwid):
        """
        ...
        note: `left` and `right` MUST be wrapped to their respective widths.
        """
        s = ''
        leftlines = left.split('\n')
        rightlines = right.split('\n')
        for n in range(max(len(leftlines), len(rightlines))):
            if n < len(leftlines):
                leftline = leftlines[n]
                s += leftline + (' '*(leftwid-len(leftline)))
            else:
                s += ' '*leftwid

            if n < len(rightlines):
                s += rightlines[n]

            s += '\n'
        return s

    if not RECSEP:
        RECSEP = '\n' + '-'*(txtwid*2) + '\n\n'

    for tag, i1, i2, j1, j2 in seqm.get_opcodes():
        if tag == 'insert':
            data += getcompareitemlines('', RECSEP.join(blist[j1:j2]), txtwid, txtwid)
        if tag == 'delete':
            data += getcompareitemlines(RECSEP.join(alist[i1:i2]), '', txtwid, txtwid)
        if tag == 'replace':
            data += getcompareitemlines(RECSEP.join(alist[i1:i2]), RECSEP.join(blist[j1:j2]), txtwid, txtwid)
        if tag == 'equal':
            continue

        data += RECSEP

    return data
    


# ----------------------------------------------------------------------


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        prog='diffendnotex2xml',
        description='See differences in XML exports from EndNote X2',
        epilog='Have a lot of fun!'
        )

    parser.add_argument('-s', '--sorted', dest='sorted', action='store_true', default=True,
                        help='uniformize the entry list order by sorting the entries')
    parser.add_argument('-S', '--not-sorted', dest='sorted', action='store_false',
                        help='uniformize the entry list order by sorting the entries')
    parser.add_argument('-w', '--width', dest='width', action='store', type=int, default=None,
                        help='display terminal width')
    parser.add_argument('-i', '--indent', dest='indent', action='store', type=int, default=None,
                        help='how much to indent lines')
    parser.add_argument('afile')
    parser.add_argument('bfile', nargs='?')

    args = parser.parse_args()

    fnkwargs = {}
    if args.width is not None:
        fnkwargs['txtwid'] = args.width
    if args.indent is not None:
        fnkwargs['addindent'] = args.indent

    if not args.bfile:
        # just display afile entries

        contents = getFormattedFileContents(args.afile, sortedentries=args.sorted,
                                            **fnkwargs)

        pydoc.pager(contents.encode(locale.getpreferredencoding()))

    else:

        contents = getFormattedDiffContents(args.afile, args.bfile, sortedentries=args.sorted,
                                            **fnkwargs)

        pydoc.pager(contents.encode(locale.getpreferredencoding()))
