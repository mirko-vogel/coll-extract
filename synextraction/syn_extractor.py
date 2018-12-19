#!/usr/bin/python
# coding=utf-8

import argparse
import codecs
import logging
from collections import Counter, defaultdict

from pyarabic import araby
import pymongo
from pymongo import MongoClient
from tqdm import tqdm
from conllu_reader import iter_tree, read_conllu


def get_collocations_from_sentence(t):
    """
    {
       pattern = "verb + prep + object"
       lempos = [lempos_1, ...]
       idx = [pos_1, pos_2, pos_3]
    }

    :param t:
    :return:

    """
    colls = []
    for n in iter_tree(t):
        lempos = u"{lemma}+{upostag}".format(**n.data)
        pos, rel, idx = n.data["upostag"], n.data["deprel"], n.data["id"]

        if not n.parent:  # a root
            continue

        # Filter:
        # - Max dist between constituents
        # - only _words_

        p_lempos = u"{lemma}+{upostag}".format(**n.parent.data)
        p_pos, p_idx = n.parent.data["upostag"], n.parent.data["id"]
        prep = next((c for c in n.children if c.data["upostag"] == "ADP"), None)
        if prep:
            prep_lempos = u"{lemma}+{upostag}".format(**prep.data)
            prep_idx = prep.data["id"]

        if rel == "nsubj" and p_pos == "VERB":
            colls.append({
                "pattern": u"فعل + فاعل",
                "lempos": [p_lempos, lempos],
                "idx": [p_idx, idx]
            })
        elif rel == "obj" and p_pos == "VERB":
            if prep:
                colls.append({
                    "pattern": u"فعل + حرف جر + مفعول به",
                    "lempos": [p_lempos, prep_lempos, lempos],
                    "idx": [p_idx, prep_idx, idx]
                })
            else:
                colls.append({
                    "pattern": u"فعل + مفعول به",
                    "lempos": [p_lempos, lempos],
                    "idx": [p_idx, idx]
                })
        if rel == "nmod" and p_pos == "NOUN":
            if prep:
                colls.append({
                    "pattern": u"اسم + حرف جر + اسم",
                    "lempos": [p_lempos, prep_lempos, lempos],
                    "idx": [p_idx, prep_idx, idx]
                })
            else:
                colls.append({
                    "pattern": u"مضاف إليه + مضاف",
                    "lempos": [p_lempos, lempos],
                    "idx": [p_idx, idx]
                })
        if rel == "amod" and p_pos == "NOUN":
                colls.append({
                    "pattern": u"اسم + صفة",
                    "lempos": [p_lempos, lempos],
                    "idx": [p_idx, idx]
                })

    return colls


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("corpus", help="Path to the dependency-parsed corpus in conluu format")
    p.add_argument("--debug", action="store_true",
                   help="Log debug messages")

    g = p.add_argument_group("Example selection parameters")
    g.add_argument("--example-count", type=int, default=10,
                   help="Number of examples to fetch for each candidate.")

    g = p.add_argument_group("Candidate filter parameters")
    g.add_argument("--max-candidate-count", type=int, default=0,
                   help="Truncate the freq-sorted candidate list")
    g.add_argument("--min-freq", type=int, default=0,
                   help="Drop candidates if freq is below min_freq")
    g.add_argument("--min-score", type=int, default=0,
                   help="Drop candidates if score is below min_score")

    g = p.add_argument_group("Storage parameters")
    g.add_argument("--db-url", type=str)
    g.add_argument("--db-name", type=str, default="muraijah")

    args = p.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Connecting to MongoDB (%s, %s).", args.db_url, args.db_name)
    db = MongoClient(args.db_url).get_database(args.db_name)
    sentences = db.get_collection("sentences")

    lemmas = db.get_collection("lemmas")
    # index for counting
    lemmas.create_index([("lemma", pymongo.ASCENDING), ("pos", pymongo.ASCENDING)], unique=True)
    # index for retrieving
    lemmas.create_index("unvocalized_lemma")

    collocations = db.get_collection("collocations")
    # Index for counting collocations
    collocations.create_index("lempos_string", unique=True)
    # Index for retrieving collocations
    collocations.create_index("lempos")

    logging.info("Importing corpus %s into db ...", args.corpus)
    lemma_counts = defaultdict(int)  # Accumulate before writing to db, otherwise too slow

    with codecs.open(args.corpus, encoding="utf-8") as f:
        for (idx, t) in tqdm(enumerate(read_conllu(f))):
            # The conllu lib is seriously bullshit ...
            nodes = sorted((n.data for n in iter_tree(t)), key=lambda n: n["id"])
            s = {
                "conllu": t.conllu,
                "words": [n["form"] for n in nodes],
                "lempos": [u"{lemma}+{upostag}".format(**n) for n in nodes],
                "idx": idx,
                "collocations": get_collocations_from_sentence(t)
            }
            _id = sentences.insert_one(s).inserted_id

            for n in nodes:
                lemma_counts[(n["lemma"], n["upostag"])] += 1

            for c in s["collocations"]:
                # FIXME: Very bad design?!
                collocations.update_one({"lempos_string": " ".join(c["lempos"])},
                                        {"$push": {"instances": _id},
                                         "$set": { "lempos": c["lempos"], "pattern": c["pattern"] } },
                                        upsert=True)

    lemmas.insert({"lemma": lemma, "pos": pos, "freq": n, "unvocalized_lemma": araby.strip_tashkeel(lemma)}
                  for (lemma, pos), n in lemma_counts.iteritems())

    # result = []
    # e = PatternExtractor(args.corpus.name, p)
    # for core in cores:
    #     logging.info("Extracting collocations for '%s' ...", " ".join(core))
    #     candidates = e.fetch_candidates(core)
    #
    #     logging.info("Filtering candidates ...")
    #     candidates = [c for c in candidates
    #                   if c.freq >= args.min_freq
    #                   and  set(c.lemma).isdisjoint(u"\"'.,،-()[]{}")]
    #     logging.info("Done. %d candidates (%d instances) remaining.",
    #                  len(candidates), sum(c.freq for c in candidates))
    #
    #     if args.max_candidate_count and len(candidates) > args.max_candidate_count:
    #         candidates = candidates[:args.max_candidate_count]
    #         logging.info("Truncated candidate list to %d.", args.max_candidate_count)
    #
    #     logging.info("Getting %d examples and marginal counts for each candidate ...", args.example_count)
    #     for c in candidates:
    #         c.fetch_marginal_count()
    #         c.fetch_examples(["word", "fullpos"], args.example_count)
    #         result.append(c.get_as_json())

    logging.info("Done.")
