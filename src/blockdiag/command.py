#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import sys
from ConfigParser import SafeConfigParser
from optparse import OptionParser
import blockdiag
import DiagramDraw
import diagparser
import utils
from builder import ScreenNodeBuilder


def parse_option():
    version = "%%prog %s" % blockdiag.__version__
    usage = "usage: %prog [options] infile"
    p = OptionParser(usage=usage, version=version)
    p.add_option('-a', '--antialias', action='store_true',
                 help='Pass diagram image to anti-alias filter')
    p.add_option('-c', '--config',
                 help='read configurations from FILE', metavar='FILE')
    p.add_option('-o', dest='filename',
                 help='write diagram to FILE', metavar='FILE')
    p.add_option('-f', '--font', default=[], action='append',
                 help='use FONT to draw diagram', metavar='FONT')
    p.add_option('-P', '--pdb', dest='pdb', action='store_true', default=False,
                 help='Drop into debugger on exception')
    p.add_option('-s', '--separate', action='store_true',
                 help='Separate diagram images for each group (SVG only)')
    p.add_option('-T', dest='type', default='PNG',
                 help='Output diagram as TYPE format')
    p.add_option('--nodoctype', action='store_true',
                 help='Do not output doctype definition tags (SVG only)')
    options, args = p.parse_args()

    if len(args) == 0:
        p.print_help()
        sys.exit(0)

    options.type = options.type.upper()
    if not options.type in ('SVG', 'PNG', 'PDF'):
        msg = "unknown format: %s" % options.type
        raise RuntimeError(msg)

    if options.type == 'PDF':
        try:
            import reportlab.pdfgen.canvas
        except ImportError:
            msg = "colud not output PDF format; Install reportlab."
            raise RuntimeError(msg)

    if options.separate and options.type != 'SVG':
        msg = "--separate option work in SVG images."
        raise RuntimeError(msg)

    if options.nodoctype and options.type != 'SVG':
        msg = "--nodoctype option work in SVG images."
        raise RuntimeError(msg)

    if options.config and not os.path.isfile(options.config):
        msg = "config file is not found: %s" % options.config
        raise RuntimeError(msg)

    configpath = options.config or "%s/.blockdiagrc" % os.environ.get('HOME')
    if os.path.isfile(configpath):
        config = SafeConfigParser()
        config.read(configpath)

        if config.has_option('blockdiag', 'fontpath'):
            fontpath = config.get('blockdiag', 'fontpath')
            options.font.append(fontpath)

    return options, args


def detectfont(options):
    fonts = options.font + \
            ['c:/windows/fonts/VL-Gothic-Regular.ttf',  # for Windows
             'c:/windows/fonts/msmincho.ttf',  # for Windows
             '/usr/share/fonts/truetype/ipafont/ipagp.ttf',  # for Debian
             '/usr/local/share/font-ipa/ipagp.otf',  # for FreeBSD
             '/System/Library/Fonts/AppleGothic.ttf']  # for MaxOS

    fontpath = None
    for path in fonts:
        if path and os.path.isfile(path):
            fontpath = path
            break

    return fontpath


def main():
    try:
        options, args = parse_option()
    except RuntimeError, e:
        sys.stderr.write("ERROR: %s\n" % e)
        return

    infile = args[0]
    if options.filename:
        outfile = options.filename
    else:
        outfile = re.sub('\..*', '', infile) + '.' + options.type.lower()

    if options.pdb:
        sys.excepthook = utils.postmortem

    fontpath = detectfont(options)

    tree = diagparser.parse_file(infile)
    if options.separate:
        diagram = ScreenNodeBuilder.build(tree, layout=False)

        for i, group in enumerate(diagram.traverse_groups()):
            group = ScreenNodeBuilder.separate(group)

            outfile2 = re.sub('.svg$', '', outfile) + ('_%d.svg' % (i + 1))
            draw = DiagramDraw.DiagramDraw(options.type, group, outfile2,
                                           font=fontpath,
                                           basediagram=diagram,
                                           antialias=options.antialias)
            draw.draw()
            draw.save()
            group.href = './%s' % os.path.basename(outfile2)

        diagram = ScreenNodeBuilder.separate(diagram)
    else:
        diagram = ScreenNodeBuilder.build(tree)

    draw = DiagramDraw.DiagramDraw(options.type, diagram, outfile,
                                   font=fontpath, antialias=options.antialias,
                                   nodoctype=options.nodoctype)
    draw.draw()
    draw.save()