# coding=utf-8
'''
Created on Mar 1, 2018

@author: mirko
'''

import sys
from itertools import chain
import manatee
from operator import iconcat

def parse_stream(s):
    """
    The format of the keyword-in-context lines depends on number of attributes,
    where `attrs` affects the return value of get_kwic(), whereas `ctxattr` affect
    the output of get_left() and get_right().
     
      * If only one attribute is requested, the return value is a pair (str, dict), where
        the string is a space-separated concatenation of the individual positions' attributes.
     
      * If several attributes are requested, the return value is a concatenation of four-tuples
        (word, _, attributes, _), e.g. (word_1, _, attributes_1, _, word_2, _, attributes_2, _, ...).
        `attributes` is a slash separated string with trailing slash
        e.g. "/PUNC/.+PUNC/PUNC"    words = s[0::4]
    
    """
    if len(s) == 2:
        return tuple( (w, ) for w in s[0].strip(" ").split(" "))
    
    words = s[0::4]
    attrs = [a.strip("/").split("/") for a in s[2::4]]
    return tuple( [w] + a for (w, a) in zip(words, attrs) )


class Collocation(object):
    '''
    classdocs
    '''

    def __init__(self, core_lemma, core_pos, coll_lemma, coll_pos, freq, coll_freq, score):
        '''
        Constructor
        '''
        self.core_lemma, self.core_pos = core_lemma, core_pos
        self.coll_lemma, self.coll_pos = coll_lemma, coll_pos
        self.freq, self.coll_freq = freq, coll_freq
        self.score = score
        self.forms = []
    
    def as_json(self):
        return { "core_lemma": self.core_lemma, "core_pos": self.core_pos,
                 "coll_lemma": self.coll_lemma, "coll_pos": self.coll_pos,
                 "freq": self.freq, "coll_freq": self.coll_freq, "score": self.score, 
                 "inflected_forms": { f.wordpos: f.as_json() for f in self.forms} }
            
    def __unicode__(self):
        return u"(Collocation %s - %s)" % (self.core_lempos, self.coll_lempos)
    
    @property
    def core_lempos(self):
        return u"%s+%s" % (self.core_lemma, self.core_pos)
    
    @property
    def coll_lempos(self):
        return u"%s+%s" % (self.coll_lemma, self.coll_pos)
    
    @staticmethod
    def fetch_collocations(corp, core_lemma, core_pos, window=(1, 1), min_freq=2):
        """
        Extract collocation candidates from the given corpus on lem-pos level, returning
        the candidates as list of Collocation objects.
        
        * window - tuple specifying the left and the right border of the extraction window,
                 (-3, -1) would capture the two preceding tokens.
        * min_freq - only include collocations occuring at least min_freq often         
        
        """
        #query = u'[lempos="%s+%s"]' % (core_lemma, core_pos) -- DOES NOT WORK
        query = u'[lemma="%s" & pos="%s"]' % (core_lemma, core_pos)
        # CHECK: Do we need that full conc?
        conc = manatee.Concordance(corp, query.encode("utf-8"), 1000000, -1)
        conc.sync() # Wait for all results to be fetched
        
        #print conc.size()
        col = manatee.CollocItems (conc,
                                   "lempos", # cattr
                                   "f",     # csorftn
                                   min_freq,       # cminfreq
                                   3,       # cminbgr -- CHECKME
                                   window[0],       # cfromw
                                   window[1],       # ctow
                                   100000        #cmaxitems
                                  )
        
        collocations = []
        while not col.eos():
            lemma, _, pos = col.get_item().decode("utf-8").rpartition("+")
            c = Collocation(core_lemma, core_pos, lemma, pos, col.get_cnt(), col.get_freq(), col.get_bgr("m")) 
            collocations.append(c)
            col.next()
            
        return collocations    
    
    def fetch_inflected_collocations(self, corpus, example_count=3):
        self.forms = InflectedCollocation.fetch_inflected_collocations(corpus, self)
        if example_count > 0:
            for c in self.forms:
                c.fetch_examples(corpus, example_count)

class InflectedCollocation(object):
    def __init__(self, core_word, core_pos, coll_word, coll_pos, freq): 
        self.core_word, self.coll_word = core_word, coll_word
        self.core_pos, self.coll_pos = core_pos, coll_pos
        self.freq = freq
        self.examples = []
    
    def as_json(self):
        e_dict = { e.ref: e.as_json() for e in self.examples }
        return { "core_word": self.core_word, "core_pos": self.core_pos,
                 "coll_word": self.coll_word, "coll_pos": self.coll_pos,
                 "freq": self.freq, "examples": e_dict }
    
    @property
    def core_wordpos(self):
        return u"%s+%s" % (self.core_word, self.core_pos)
    
    @property
    def coll_wordpos(self):
        return u"%s+%s" % (self.coll_word, self.coll_pos)
    
    @property
    def wordpos(self):
        """ Returns the collocation as word-pos tokens """
        return u"%s %s" % (self.core_wordpos, self.coll_wordpos)
    
    def __unicode__(self):
        return u"(InflectedCollocation %s - %s)" % (self.core_wordpos, self.coll_wordpos)
    
    @staticmethod
    def fetch_inflected_collocations(corpus, c, min_freq=3):
        """
        Create a list of inflected collocations for given collocation c
        in given corpus
        
        """
        query = u'[lemma="%s" & pos="%s"][lemma="%s" & pos="%s"]' \
            % (c.core_lemma, c.core_pos, c.coll_lemma, c.coll_pos)
        
        conc = manatee.Concordance(corpus, query, 1000000, -1)
        conc.sync()
        words = manatee.StrVector()
        freqs = manatee.NumVector()
        norms = manatee.NumVector()
        
        # "word/e 0~0>0"
        crit = "word 0 word 1"
        corpus.freq_dist(conc.RS(), crit, min_freq, words, freqs, norms)
        freq_table = [(w.split(), f) for w, f in zip(words, freqs)]
        freq_table.sort(key=lambda x:x[1], reverse=True)
        
        collocations = []
        for ((w1, w2), f) in freq_table:
            collocations.append(InflectedCollocation(w1.decode("utf-8"), c.core_pos,
                                                     w2.decode("utf-8"), c.coll_pos, f))

        return collocations
    
    def fetch_examples(self, corpus, example_count=5):
        """
        """
        query = u'[word="%s" & pos="%s"] [word="%s" & pos="%s"]' \
            % (self.core_word, self.core_pos, self.coll_word, self.coll_pos)

        conc = manatee.Concordance(corpus, query, example_count, -1)
        conc.sync()
    
        #=======================================================================
        # if gdex:
        #     if '/usr/lib/python2.7/dist-packages/bonito' not in sys.path:
        #         sys.path.insert (0, '/usr/lib/python2.7/dist-packages/bonito')
        #     import gdex_old as gdex
        #     cnt = count # How many lines to score
        #     best = gdex.GDEX(corp)
        #     best.entryConc (conc)
        #     score_index_toknum = best.best_k_with_toknum(cnt, cnt)
        #     gdex_scores = dict([(toknum, score) for score, index, toknum in score_index_toknum])
        #     conc.set_sorted_view(manatee.IntVector([index for score, index, toknum in score_index_toknum]))
        #=======================================================================
        
        fromline, toline = 0, example_count
        leftctx, rightctx = "-1:s", "1:s"
        refs = "doc,s"
        attrs = "word" #"word,pos,fullpos"
        ctxattrs = attrs
        structs = ",ltr"
    
        kl = manatee.KWICLines (conc.corp(), conc.RS(True, fromline, toline), leftctx, rightctx, attrs, ctxattrs, structs, refs)
    
        while kl.nextline():
            lc = parse_stream(kl.get_left())
            kw = parse_stream(kl.get_kwic())
            rc = parse_stream(kl.get_right())
            words = [x[0].decode("utf-8") for x in chain(lc, kw, rc)]
            # Get refs should be a single one as we do not cross sentence boundaries
            self.examples.append(CollocationExample(words, [len(lc), len(lc)+1], kl.get_refs()))

class CollocationExample(object):
    def __init__(self, words, coll_pos, ref):
        """
        words - list of unicode words
        coll_pos - tuple of word positions
        ref
        
        """
        self.words = words
        self.coll_pos = coll_pos
        self.coll = u" ".join(words[k] for k in coll_pos) 
        self.ref = ref

    def get_highlighted(self, format_str="%s"):
        """
        Returns the example as a string with collocation words highlighted
        
        >>> CollocationExample(["a", "b", "c"], [0, 2], "").get_highlighted("<%s>")
        '<a> b <c>'
        
        """
        return " ".join(format_str % w if n in self.coll_pos else w
                        for (n, w) in enumerate(self.words))
                                
    def as_json(self):
        return { "sentence": " ".join(self.words), "coll_pos": self.coll_pos, "ref": self.ref }
    
    def __unicode__(self):
        return u"(CollocationExample %s @%s)" % (self.coll, self.ref) 
    

from tqdm import tqdm


class ManateeCollocationExtractor(object):
    """
    ManateeCollocationExtractor("/home/mirko/Projects/arabic_corpora/manatee_corpora/registry/lcc", u"اتفاقية", u"NOUN")
    e.fetch_collocation_candidates()
    
    """
    def __init__(self, corpus_path, lemma, pos):
        """
        
        """
        self.corpus = manatee.Corpus (corpus_path)
        self.lemma, self.pos = lemma, pos
        
        #query = u'[lempos="%s+%s"]' % (core_lemma, core_pos) -- DOES NOT WORK
        query = u'[lemma="%s" & pos="%s"]' % (lemma, pos)
        self.conc = manatee.Concordance(self.corpus, query.encode("utf-8"), 1000000, -1) # Returns immediately        
        
    def extract_noun_adj_collocations(self, min_freq):
        candidates = self.fetch_collocation_candidates((1,1), min_freq)
        
    
    
    def fetch_collocation_candidates(self, window=(1, 1), min_freq=2):
        """
        Extract collocation candidates on lem-pos level, returning a list of tuples
        (lemma, pos, freq, score).
        
        * window - tuple specifying the left and the right border of the extraction window,
                 (-3, -1) would capture the two preceding tokens.
        * min_freq - only include collocations occuring at least min_freq often         
        
        """

        self.conc.sync() # Wait for all results to be fetched
        r = manatee.CollocItems (self.conc,
                                   "lempos", # cattr
                                   "f",     # csorftn
                                   min_freq,       # cminfreq
                                   3,       # cminbgr -- CHECKME
                                   window[0],       # cfromw
                                   window[1],       # ctow
                                   100000        #cmaxitems
                                  )
        
        candidates = []
        while not r.eos():
            coll_lemma, _, coll_pos = r.get_item().decode("utf-8").rpartition("+")
            # We do not store the collocator frequency col.get_cnt(),
            candidates.append( (coll_lemma, coll_pos, r.get_freq(), r.get_bgr("m")) )
            r.next()
            
        return candidates


import pymongo

def extract_candidates_into_db(corpus_path, mongodb_collection, core_lemma,
                               core_pos, patterns = ["noun+ADJ", "noun+NOUN"]):
    """
    For every given pattern, instanciate an appropriate collocation extractor,
    extract collocations for given core and add to mongodb collection
    
    """
    corp = manatee.Corpus(corpus_path)
    
    # REWRITEME
    raw_candidates = Collocation.fetch_collocations(corp, core_lemma, core_pos, min_freq=10)
    candidates = filter(lambda c: c.coll_pos in ("ADJ", "NOUN"), raw_candidates)
    for c in tqdm(candidates):
        c.fetch_inflected_collocations(corp)
        mongodb_collection.insert_one(c.as_json())
    
 
if __name__ == "__main__":
    #cloud_url = "mongodb://admin:b4AAPjheEzxAuYFW@cluster0-shard-00-00-1utjf.mongodb.net:27017,cluster0-shard-00-01-1utjf.mongodb.net:27017,cluster0-shard-00-02-1utjf.mongodb.net:27017/test?ssl=true&replicaSet=Cluster0-shard-0&authSource=admin"
    corpus_path = "/home/mirko/Projects/arabic_corpora/manatee_corpora/registry/lcc"
    collection = pymongo.MongoClient().collocation_review.candidates
    core_lemma = sys.argv[1].decode("utf-8")
    core_pos = u"NOUN"

    extract_candidates_into_db(corpus_path,collection, core_lemma, core_pos)
    
        