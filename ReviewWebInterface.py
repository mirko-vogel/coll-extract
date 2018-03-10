'''
Created on Mar 10, 2018

@author: mirko
'''
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
        self.db = mongodb
        
    @cherrypy.expose
    def index(self):
        r = self.db.candidates.find({}, {"_id": 0, "core_lemma": 1, "core_pos": 1, "coll_pos": 1})
        cores = defaultdict(lambda: defaultdict(int))
        for c in r:
            cores[(c["core_lemma"], c["core_pos"])][c["coll_pos"]] +=1
        
        tmpl = file("templates/candidates_overview.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [{"cores": dict(cores.iteritems())}])
        return unicode(t).encode("utf8")

    @cherrypy.expose
    def candidates(self, core_lemma, core_pos, coll_pos):
        r = self.db.candidates.find({"core_lemma":core_lemma, "core_pos": core_pos, "coll_pos": coll_pos})
        tmpl = file("templates/candidates_review.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [{"candidates": r}])
        return unicode(t).encode("utf8")
    
    @cherrypy.expose
    def rate_collocation(self, _id, rating):
        """
        
        """
        path = u"rating.%s" % rating
        r = self.db.candidates.update_one({"_id": ObjectId(_id)}, {"$inc": {path: 1}})
        r2 = self.db.feedback.insert_one({"time": ctime(), "user": "mv",
                                          "type": "rate_collocation", "rating": rating})
        pass


    @cherrypy.expose
    def rate_example(self, _id, rating):
        """
        
        """
        #path = u"inflected_forms.%s.examples.%s.user_feedback" % (form, ref)
        pass
    
if __name__ == "__main__":
    server = ReviewWebInterface(pymongo.MongoClient().collocation_review)
    cherrypy.quickstart(server, '/', "cherrypy.conf")