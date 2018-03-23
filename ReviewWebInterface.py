#!/usr/bin/python
'''
Created on Mar 10, 2018

@author: mirko
'''
import argparse
from collections import defaultdict
from time import ctime

import cherrypy
from Cheetah.Template import Template

import pymongo
from bson.objectid import ObjectId

class ReviewWebInterface(object):
    """
    Collocations used:
    - candidates
    - feedback
    
    """
    def __init__(self, mongodb):
        """

        :type mongodb: pymongo.database.Database
        """
        self.db = mongodb
        
    def assure_logged_in(self):
        try:
            return cherrypy.session['user_name']
        except KeyError:
            raise cherrypy.HTTPRedirect("/login_page")

    @cherrypy.expose
    def set_user_info(self, user_name, user_email):
        cherrypy.session['user_name'] = user_name
        cherrypy.session['user_email'] = user_email
        raise cherrypy.HTTPRedirect("/")

    @cherrypy.expose
    def login_page(self):
        s = cherrypy.session
        tmpl = file("templates/login.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [{"user_name": s.get("user_name"), "user_email": s.get("user_email")}])
        return unicode(t).encode("utf8")
    
    @cherrypy.expose
    def index(self):
        user_name = self.assure_logged_in()
        # Yes, this should be done with $group
        r = self.db.candidates.find({}, {"_id": 1, "core_lempos": 1, "pattern": 1, "ratings": 1})
        cores = {}
        for c in r:
            if c["core_lempos"] not in cores:
                cores[c["core_lempos"]] = {}
            if c["pattern"] not in cores[c["core_lempos"]]:
                cores[c["core_lempos"]][c["pattern"]] = 0
            if not "ratings" in c:
                cores[c["core_lempos"]][c["pattern"]] += 1

        r = self.db.feedback.find({}, {"_id": 0, "user": 1})
        d = {}
        for c in r:
            d.setdefault(c["user"], 0)
            d[c["user"]] += 1

        tmpl = file("templates/candidates_overview.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [{"cores": dict(cores.iteritems()),
                                          "user_name": user_name, "contributions": d}])
        return unicode(t).encode("utf8")
    
    @cherrypy.expose
    def candidates(self, core_lempos, pattern):
        user_name = self.assure_logged_in()
        r = self.db.candidates.find({"core_lempos":core_lempos, "pattern": pattern})
        tmpl = file("templates/candidates_review.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [{"candidates": r, "pattern": pattern, "core_lempos": core_lempos}])
        return unicode(t).encode("utf8")

    @cherrypy.expose
    def candidate(self, _id):
        user_name = self.assure_logged_in()
        r = self.db.candidates.find_one({"_id": ObjectId(_id)})
        tmpl = file("templates/candidate_review.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [{"candidate": r}])
        return unicode(t).encode("utf8")

    @cherrypy.expose
    def rate_collocation(self, _id, rating):
        """
        
        """
        user_name = self.assure_logged_in()
        path = u"ratings.%s" % user_name
        r = self.db.candidates.update_one({"_id": ObjectId(_id)}, {"$set": {path: rating}})
        r2 = self.db.feedback.insert_one({"time": ctime(), "user": user_name, "collocation_id": _id,
                                          "type": "rate_collocation", "rating": rating})


    @cherrypy.expose
    def rate_example(self, _id, e_idx, rating):
        """
        
        """
        user_name = self.assure_logged_in()
        path = u"examples.%s.ratings.%s" % (e_idx, user_name)
        r = self.db.candidates.update_one({"_id": ObjectId(_id)}, {"$set": {path: rating}})
        r2 = self.db.feedback.insert_one({"time": ctime(), "user": user_name,
                                          "collocation_id": _id, "example_idx": e_idx,
                                          "type": "rate_example", "rating": rating})
    
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--db-name", type=str, default="collocation_review")
    args = p.parse_args()

    cherrypy.config.update({"server.socket_port": args.port})
    server = ReviewWebInterface(pymongo.MongoClient().get_database(args.db_name))
    cherrypy.quickstart(server, '/', "cherrypy.conf")