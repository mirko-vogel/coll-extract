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
import cherrypy_cors

import urllib
from collections import defaultdict

import itertools
from Cheetah.Template import Template
from bson import ObjectId
from pyarabic import araby
from pymongo import MongoClient

def cors():
  if cherrypy.request.method == 'OPTIONS':
    # preflign request
    # see http://www.w3.org/TR/cors/#cross-origin-request-with-preflight-0
    cherrypy.response.headers['Access-Control-Allow-Methods'] = 'POST'
    cherrypy.response.headers['Access-Control-Allow-Headers'] = 'content-type'
    cherrypy.response.headers['Access-Control-Allow-Origin']  = '*'
    # tell CherryPy no avoid normal handler
    return True
  else:
    cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'

cherrypy.tools.cors = cherrypy._cptools.HandlerTool(cors)




class CollocationAPI(object):
    exposed = True

    def __init__(self, db):
        """

        :type db: MongoClient
        """
        self.sentences = db.get_collection("sentences")
        self.collocations = db.get_collection("collocations")
        self.lemmas = db.get_collection("lemmas")


    @cherrypy.tools.accept(media='application/json')
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):
        data = cherrypy.request.json
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
        return {}

    def OPTIONS(self):
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'POST'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'content-type'
        cherrypy.response.headers['Access-Control-Allow-Origin']  = '*'
        return True


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

    def get_lemma_freq(self, lempos):
        lemma, pos = lempos.split("+")
        return self.lemmas.find_one({"lemma": lemma, "pos": pos}, {"freq": 1, "_id": 0})["freq"]

    @cherrypy.expose
    def show(self, lempos):
        """
        :param lempos: space separated sequence of core lempos
        :return: html page

        """
        core_lempos = lempos.split(" ")
        colls = self.get_collocations(core_lempos)

        params = {"lempos": core_lempos, "lempos_freqs": [self.get_lemma_freq(lp) for lp in core_lempos],
                  "collocations": colls}
        tmpl = file("../templates/collocations.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList=[params])
        return unicode(t).encode("utf8")

    def search_candidates(self, w):
        """
        For a space separated list of words, returns a matching list if lists of lempos.

        """
        candidate_lists = []
        for word in w.split():
            r = self.lemmas.find({"lemma": word}, {"lemma": 1, "_id": 0, "pos": 1})
            if not r.count():
                r = self.lemmas.find({"unvocalized_lemma": araby.strip_tashkeel(word)},
                                     {"lemma": 1, "_id": 0, "pos": 1})

            candidate_lists.append([u"{lemma}+{pos}".format(**d) for d in r])

        return tuple(itertools.product(*candidate_lists))

    @cherrypy.expose
    def search(self, w):
        """Returns html page"""
        candidates = self.search_candidates(w)
        if len(candidates) == 1:
            q = urllib.urlencode({"lempos": " ".join(candidates[0]).encode("utf-8")})
            raise cherrypy.HTTPRedirect("show?" + q)

        else:
            tmpl = file("../templates/select_lemma.tmpl").read().decode("utf-8")
            t = Template(tmpl, searchList=[{"candidates": candidates, "word": w}])
            return unicode(t).encode("utf8")

    @cherrypy.expose
    def group_collocations(self, lempos, pattern, core_indexes):
        core_indexes = map(int, core_indexes.split(","))
        # FIXME: The result needs to be filtered for core indexes!
        result = self.collocations.find({"lempos": lempos, "pattern": pattern})
        tmpl = file("../templates/group_collocations.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList=[
            {"collocations": result, "lempos": lempos, "pattern": pattern, "core_indexes": core_indexes}])
        return unicode(t).encode("utf8")

    @cherrypy.expose
    def get_examples(self, coll_id, max_count=10):
        d = self.collocations.find_one({"_id": ObjectId(coll_id)})
        r = self.sentences.find({"_id": {"$in": d["instances"]}})
        sentences = list(next(r) for _ in range(max_count))
        params = {"collocation": d, "examples": sentences}
        tmpl = file("../templates/examples.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList=[params])
        return unicode(t).encode("utf8")

    # ---------------- API: Query db -----------------------

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def search_as_json(self, w):
        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"
        return self.search_candidates(w)

    @cherrypy.expose
    @cherrypy.config(**{'tools.cors.on': True})
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def api(self):
        data = cherrypy.request.json
        pass

    @cherrypy.expose
    @cherrypy.config(**{'tools.cors.on': True})
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def collocations_as_json(self):
        """
        Returns collocations containing a given lempos, eventually restricting results
        to the given pattern and the given core indexes

        """
        data = cherrypy.request.json
        lempos = data["lempos"]
        pattern = data.get("pattern", None)
        core_indexes = data.get("core_indexes", None)
        min_freq = data.get("min_freq", 2)

        q = {"lempos": lempos}
        if pattern:
            q["pattern"] = pattern

        colls = list(c for c in self.collocations.find(q, {"_id": 0})
                     if len(c["instances"]) >= min_freq)

        if core_indexes:
            core_indexes = map(int, core_indexes.split(","))
            pass
            # FIXME: The result needs to be filtered for core indexes!

        # Return freq instead of list of instance object ids
        for c in colls:
            c["freq"] = len(c.pop("instances"))
            # FIXME: Better way to guarantee certain fields are present
            c.setdefault("instance_ratings", {})

        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"
        return colls

    @cherrypy.expose
    @cherrypy.config(**{'tools.cors.on': True})
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def get_instances(self):
        """
        Returns examples for a collocation identified by its lempos and its pattern
        The returned list consists of good examples, followed by unrated examples, with
        a maximum length of max_count.

        """
        p = cherrypy.request.json
        d = self.collocations.find_one({"lempos_string": p["lempos"], "pattern": p["pattern"]},
                                       {"instances": 1, "instance_ratings": 1})
        if not d:
            return []

        ratings = d.get("instance_ratings", {}).items()
        good_ids = list(ObjectId(_id) for (_id, rating) in ratings if rating)
        bad_ids = list(ObjectId(_id) for (_id, rating) in ratings if not rating)
        unrated_ids = set(d["instances"]).difference(good_ids + bad_ids)

        n = p.get("max_count")
        if n:
            unrated_ids = itertools.islice(unrated_ids, n - len(good_ids))
        instance_ids = good_ids[:n] + list(unrated_ids)

        r = self.sentences.find({"_id": {"$in": instance_ids}}, {"conllu": 0})
        good, unrated = [], []
        for s in r:
            if s["_id"] in good_ids:
                good.append(s)
            else:
                unrated.append(s)
            # FIXME: Ugly mapping of object id to string (for serealization to JSON)
            s["_id"] = str(s["_id"])

        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"
        return good + unrated

    # ---------------- API: update db -----------------------

    def update_one(self, selector, updater):
        """ Updates the collocation collection """
        cherrypy.response.headers['Access-Control-Allow-Origin'] = "*"
        r = self.collocations.update_one(selector, updater)
        # FIXME: Add updating the "changes table"
        return {"success": True}

    @cherrypy.expose
    @cherrypy.config(**{'tools.cors.on': True})
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def rate_collocation(self):
        """ Rates a collocation identified by its lempos and its pattern """
        p = cherrypy.request.json
        return self.update_one({"lempos_string": p["lempos"], "pattern": p["pattern"]},
                               {"$set": {"rating": p["rating"]}})

    @cherrypy.expose
    @cherrypy.config(**{'tools.cors.on': True})
    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def rate_instance(self):
        """
        Rates an instance, identified by its sentence id, of a collocation,
        identified by its lempos and its pattern
        """
        p = cherrypy.request.json
        return self.update_one({"lempos_string": p["lempos"], "pattern": p["pattern"]},
                            {"$set": {"instance_ratings.%s" % p["sentence_id"]: p["rating"]}})


    @cherrypy.expose
    @cherrypy.tools.json_out()
    def group_collocations(self, lempos, pattern, for_lempos, group):
        """
         Rates a collocation identified by its lempos and its pattern,
         either as correct or as incorrect.

         """
        return self.update_one({"lempos_string": lempos, "pattern": pattern},
                            {"$set": {"classification.%s" % for_lempos: group}})


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
