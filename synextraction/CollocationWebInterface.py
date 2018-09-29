#!/usr/bin/python
# coding=utf-8
'''
Bla bal

@author:     Mirko Vogel
'''
import argparse
import logging
import sys, os

import cherrypy, cherrypy.lib.static
from collections import defaultdict

from Cheetah.Template import Template
from bson import ObjectId
from pyarabic import araby
from pymongo import MongoClient


class CollocationWebInterface(object):
    def __init__(self, db):
        """

        :type db: MongoClient
        """
        self.sentences = db.get_collection("sentences")
        self.collocations = db.get_collection("collocations")
        self.lemmas = db.get_collection("lemmas")
        
    @cherrypy.expose
    def index(self):
        return self.show(u"قَلَّب")

    @cherrypy.expose
    def show(self, lempos):
        """Returns html page"""
        colls = defaultdict(list)
        for d in self.collocations.find({"lempos": lempos}):
            core_idx = d["lempos"].index(lempos)
            colls[(d["pattern"], core_idx)].append(d)
        params = { "lempos": lempos, "collocations": colls }
        tmpl = file("../templates/collocations.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [params])
        return unicode(t).encode("utf8")

    @cherrypy.expose
    def search(self, w):
        """Returns html page"""
        r = self.lemmas.find({"lemma": w}, {"lemma": 1, "_id": 0, "pos": 1})
        if not r.count():
            r = self.lemmas.find({"unvocalized_lemma": araby.strip_tashkeel(w)},
                                 {"lemma": 1, "_id": 0, "pos": 1})

        if r.count() == 1:
            lempos = u"{lemma}+{pos}".format(**next(r))
            return self.show(lempos)

        else:
            tmpl = file("../templates/select_lemma.tmpl").read().decode("utf-8")
            t = Template(tmpl, searchList=[{"lempos": list(r), "word": w}])
            return unicode(t).encode("utf8")


    @cherrypy.expose
    def get_examples(self, coll_id, max_count = 10):
        d = self.collocations.find_one({"_id": ObjectId(coll_id)})
        r = self.sentences.find({"_id": { "$in": d["instances"]} })
        sentences = list(next(r) for _ in range(max_count))
        params = {"collocation": d, "examples": sentences}
        tmpl = file("../templates/examples.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList=[params])
        return unicode(t).encode("utf8")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    g = p.add_argument_group("Storage parameters")
    g.add_argument("--db-url", type=str)
    g.add_argument("--db-name", type=str, default="muraijah")
    args = p.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

    logging.info("Connecting to MongoDB (%s, %s).", args.db_url, args.db_name)
    db = MongoClient(args.db_url).get_database(args.db_name)
    server = CollocationWebInterface(db)
    
    cherrypy.quickstart(server, '/', "../cherrypy.conf")