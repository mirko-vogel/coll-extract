#!/usr/bin/python
# coding=utf-8
import sys
from collections import defaultdict
import codecs

import nltk
from nltk.collocations import BigramCollocationFinder

"""
Web Interface


"""
from CollocationWebInterface import CollocationWebInterface

#CORE_FIRST_PATTERNS = [("noun", "NOUN"), ("noun", "ADJ")]#CORE_SECOND_PATTERNS = [("VERB", "noun"), ("NOUN", "noun")]

class CollocationExtractor():
    def __init__(self, fn, freq):
        """ Reads corpus from given file and collects bigrams """
        self.finder = BigramCollocationFinder.from_words(word_from_file(fn))
        self.finder.apply_freq_filter(freq)
        print "Read %d words. %d bigrams after pruning." \
                % (self.wordcount, self.bigramcount)
            
        self.scored_bigrams = defaultdict(lambda : defaultdict(list))
  
    def score(self):
        """ """
        score_fn = nltk.collocations.BigramAssocMeasures.pmi
        
        for (w1, w2), score in self.finder._score_ngrams(score_fn):
            l1, t1 = w1.rsplit("/", 1)
            l2, t2 = w2.rsplit("/", 1)
            w1_pattern = "%s + %s" % (t1.lower(), t2)
            w2_pattern = "%s + %s" % (t1, t2.lower())
            count = self.finder.ngram_fd[(w1, w2)]
            
            #print "%s %s %s" % (a, b, score)
            self.scored_bigrams[w1][w1_pattern].append((l2, score, count))
            self.scored_bigrams[w2][w2_pattern].append((l1, score, count))


    def prettyprint(self, w, topn = 20):
        for (pattern, collocations) in self.scored_bigrams[w].iteritems():
            sys.stdout.write("=== %s ===\n" % pattern)
            #sys.stdout.write(unicode(collocations))
            sorted_collocations = sorted(collocations, key=lambda x: -x[1])[:topn]
            for n, (collocator, score, count) in enumerate(sorted_collocations):
                sys.stdout.write("%.2f\t%d\t%s\t%d\n" % (score, count, collocator, n + 1))

    @property
    def wordcount(self):
        return self.finder.word_fd.N()
    
    @property
    def bigramcount(self):
        return self.finder.ngram_fd.N()


def word_from_file(_fn):
    for n, l in enumerate(codecs.open(_fn, "rb", "utf-8")):
        for w in l.split():
            yield w
        if n % 50000 == 0:
            print n

if __name__ == '__main__':
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout)
    
    fn = sys.argv[1]
    freq = int(sys.argv[2])
    ce = CollocationExtractor(fn, freq)
    ce.score()
    
    while True:
        word = raw_input("> ").decode("utf-8")
        ce.prettyprint(word)
    
