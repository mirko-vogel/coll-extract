#!/usr/bin/python
# coding=utf-8
'''
Bla bal

@author:     Mirko Vogel
'''
import sys, os

import cherrypy, cherrypy.lib.static
from Cheetah.Template import Template

import CollocationExtractor


class CollocationWebInterface(object):
    def __init__(self, ce):
        self.ce = ce
        
    @cherrypy.expose
    def index(self):
        return self.show("")

    @cherrypy.expose
    def show(self, w):
        """Returns html page"""
        c = self.ce.scored_bigrams[w]
        if not c:
            c = self.ce.scored_bigrams[w + "/NOUN"]
        if not c:
            c = self.ce.scored_bigrams[w + "/V"]
        if not c:
            c = self.ce.scored_bigrams[w + "/ADJ"]
        params = { "word": w, "collocations": c }
        
        tmpl = file("templates/collocations.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [params])
        return unicode(t).encode("utf8")

    
if __name__ == '__main__':
    ce = CollocationExtractor.CollocationExtractor(sys.argv[1], int(sys.argv[2]))
    ce.score()
    server = CollocationWebInterface(ce)
    
    cherrypy.quickstart(server, '/', "cherrypy.conf")