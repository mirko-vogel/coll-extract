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
        tmpl = file("templates/login.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [{}])
        return unicode(t).encode("utf8")
    
    @cherrypy.expose
    def index(self):
        user_name = self.assure_logged_in()
        r = self.db.candidates.find({}, {"_id": 0, "core_lemma": 1, "core_pos": 1, "coll_pos": 1})
        cores = defaultdict(lambda: defaultdict(int))
        for c in r:
            cores[(c["core_lemma"], c["core_pos"])][c["coll_pos"]] +=1
        
        tmpl = file("templates/candidates_overview.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [{"cores": dict(cores.iteritems()),
                                          "user_name": user_name}])
        return unicode(t).encode("utf8")
    
    @cherrypy.expose
    def candidates(self, core_lemma, core_pos, coll_pos):
        user_name = self.assure_logged_in()
        r = self.db.candidates.find({"core_lemma":core_lemma, "core_pos": core_pos, "coll_pos": coll_pos})
        tmpl = file("templates/candidates_review.tmpl").read().decode("utf-8")
        t = Template(tmpl, searchList = [{"candidates": r}])
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
    def rate_example(self, _id, ic_key, ref, rating):
        """
        
        """
        #path = u"inflected_forms.%s.examples.%s.user_feedback" % (form, ref)
        user_name = self.assure_logged_in()
        path = u"inflected_forms.%s.examples.%s.ratings.%s" % (ic_key, ref, user_name)
        r = self.db.candidates.update_one({"_id": ObjectId(_id)}, {"$set": {path: rating}})
        r2 = self.db.feedback.insert_one({"time": ctime(), "user": user_name,
                                          "collocation_id": _id, "example_ref": ref,
                                          "type": "rate_example", "rating": rating})
    
if __name__ == "__main__":
    server = ReviewWebInterface(pymongo.MongoClient().collocation_review)
    cherrypy.quickstart(server, '/', "cherrypy.conf")