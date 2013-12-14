"""Diagnostic functions, mainly for use when doing tech support."""
from StringIO import StringIO
from HTMLParser import HTMLParser
from bs4 import BeautifulSoup, __version__
from bs4.builder import builder_registry
import os
import traceback
import sys

def diagnose(data):
    """Diagnostic suite for isolating common problems."""
    print "Diagnostic running on Beautiful Soup %s" % __version__
    print "Python version %s" % sys.version

    basic_parsers = ["html.parser", "html5lib", "lxml"]
    for name in basic_parsers:
        for builder in builder_registry.builders:
            if name in builder.features:
                break
        else:
            basic_parsers.remove(name)
            print (
                "I noticed that %s is not installed. Installing it may help." %
                name)

    if 'lxml' in basic_parsers:
        basic_parsers.append(["lxml", "xml"])
        from lxml import etree
        print "Found lxml version %s" % ".".join(map(str,etree.LXML_VERSION))

    if 'html5lib' in basic_parsers:
        import html5lib
        print "Found html5lib version %s" % html5lib.__version__

    if hasattr(data, 'read'):
        data = data.read()
    elif os.path.exists(data):
        print '"%s" looks like a filename. Reading data from the file.' % data
        data = open(data).read()
    elif data.startswith("http:") or data.startswith("https:"):
        print '"%s" looks like a URL. Beautiful Soup is not an HTTP client.' % data
        print "You need to use some other library to get the document behind the URL, and feed that document to Beautiful Soup."
        return
    print

    for parser in basic_parsers:
        print "Trying to parse your markup with %s" % parser
        success = False
        try:
            soup = BeautifulSoup(data, parser)
            success = True
        except Exception, e:
            print "%s could not parse the markup." % parser
            traceback.print_exc()
        if success:
            print "Here's what %s did with the markup:" % parser
            print soup.prettify()

        print "-" * 80

def lxml_trace(data, html=True):
    """Print out the lxml events that occur during parsing.

    This lets you see how lxml parses a document when no Beautiful
    Soup code is running.
    """
    from lxml import etree
    for event, element in etree.iterparse(StringIO(data), html=html):
        print("%s, %4s, %s" % (event, element.tag, element.text))

class AnnouncingParser(HTMLParser):
    """Announces HTMLParser parse events, without doing anything else."""
    def handle_starttag(self, name, attrs):
        print "%s START" % name

    def handle_endtag(self, name):
        print "%s END" % name

    def handle_data(self, data):
        print "%s DATA" % data

    def handle_charref(self, name):
        print "%s CHARREF" % name

    def handle_entityref(self, name):
        print "%s ENTITYREF" % name

    def handle_comment(self, data):
        print "%s COMMENT" % data

    def handle_decl(self, data):
        print "%s DECL" % data

    def unknown_decl(self, data):
        print "%s UNKNOWN-DECL" % data

    def handle_pi(self, data):
        print "%s PI" % data

def htmlparser_trace(data):
    """Print out the HTMLParser events that occur during parsing.

    This lets you see how HTMLParser parses a document when no
    Beautiful Soup code is running.
    """
    parser = AnnouncingParser()
    parser.feed(data)

if __name__ == '__main__':
    diagnose(sys.stdin.read())
