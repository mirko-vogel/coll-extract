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

import itertools
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

    def get_collocations(self, core_lempos):
        """
        Get collocations from db containing the passed lempos.

        :param core_lempos: list of lempos
        :return: dictionary of (pattern, core_indexes) -> collocations

        """
        # FIXME? Do not retreive instances, only instance count
        result = self.collocations.find({"lempos": {"$all": core_lempos}})
        colls = defaultdict(list)
        for c in result:
            # The $all operator returns all collocations containing the lempos specified
            # in the query regardeless of the order. We want ascending order.
            core_indexes = tuple(c["lempos"].index(lempos) for lempos in core_lempos)
            if not all(a < b for (a, b) in zip(core_indexes[:-1], core_indexes[1:])):
                continue

            # Group collocations not only by pattern, but by the position of the core lempos
            # in that pattern, e.g. NOUN + noun and noun + NOUN.
            colls[(c["pattern"], core_indexes)].append(c)

        return colls

    @cherrypy.expose
    def show(self, lempos):
        """
        :param lempos: space separated sequence of core lempos
        :return: html page

        """
        core_lempos = lempos.split(" ")
        colls = self.get_collocations(core_lempos)

        params = { "lempos": core_lempos, "collocations": colls }
        tmpl = file("../templates/collocations.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [params])
        return unicode(t).encode("utf8")

    @cherrypy.expose
    def search(self, w):
        """Returns html page"""
        candidate_lists = []
        for word in w.split():
            r = self.lemmas.find({"lemma": word}, {"lemma": 1, "_id": 0, "pos": 1})
            if not r.count():
                r = self.lemmas.find({"unvocalized_lemma": araby.strip_tashkeel(word)},
                                     {"lemma": 1, "_id": 0, "pos": 1})

            candidate_lists.append([u"{lemma}+{pos}".format(**d) for d in r])

        candidates = tuple(itertools.product(*candidate_lists))
        if len(candidates) == 1:
            return self.show(" ".join(candidates[0]))

        else:
            tmpl = file("../templates/select_lemma.tmpl").read().decode("utf-8")
            t = Template(tmpl, searchList=[{"candidates": candidates, "word": w}])
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