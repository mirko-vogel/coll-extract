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
from pymongo import MongoClient


class CollocationWebInterface(object):
    def __init__(self, db):
        """

        :type db: MongoClient
        """
        self.sentences = db.get_collection("sentences")
        self.collocations = db.get_collection("collocations")
        
    @cherrypy.expose
    def index(self):
        return self.show(u"قَلَّب")

    @cherrypy.expose
    def show(self, w):
        """Returns html page"""
        r = self.collocations.find({"lemmas": w})
        colls = defaultdict(list)
        for d in r:
            core_idx = d["lemmas"].index(w)
            colls[(d["pattern"], core_idx)].append(d)
        params = { "word": w, "collocations": colls }
        tmpl = file("../templates/collocations.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [params])
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