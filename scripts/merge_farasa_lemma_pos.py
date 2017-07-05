#!/usr/bin/python

import sys
import codecs
from itertools import izip

f_pos = codecs.open(sys.argv[1], "r", "utf-8")
f_lemma = codecs.open(sys.argv[2], "r", "utf-8")
stdout = codecs.getwriter('utf8')(sys.stdout)

for (pos_tagged, lemmatized) in izip(f_pos , f_lemma):
	tok_pos_pairs = (tok.rsplit("/", 1) for tok in pos_tagged.split(" ")[1:-2])
	pos_tags = (pair[1] for pair in tok_pos_pairs if '+' not in pair[0])
	lemma_toks = lemmatized.strip().split(" ")
	lemma_pos_pairs = ("%s/%s" % (lemma, pos.split("-")[0]) \
				for (lemma, pos) in izip(lemma_toks, pos_tags))
	stdout.write(" ".join(lemma_pos_pairs))
	stdout.write("\n")

