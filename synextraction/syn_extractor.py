#!/usr/bin/python
# coding=utf-8

import argparse
import codecs
import logging
from collections import Counter, defaultdict

import pymongo
from pymongo import MongoClient
from tqdm import tqdm
from conllu_reader import iter_tree, read_conllu


def get_collocations_from_sentence(t):
    """
    {
       pattern = "verb + prep + object"
       verb = lemma of verb
       prep = lemma of prep
       object = lemma of object
       idx = [pos_1, pos_2, pos_3]
    }

    :param t:
    :return:

    """
    colls = []
    for n in iter_tree(t):
        lemma, tag, rel, idx = n.data["lemma"], n.data["upostag"], n.data["deprel"], n.data["id"]

        if not n.parent:  # a root
            continue

        p_lemma, p_tag, p_idx = n.parent.data["lemma"], n.parent.data["upostag"], n.parent.data["id"]
        prep = next((c for c in n.children if c.data["upostag"] == "ADP"), None)

        if rel == "nsubj" and p_tag == "VERB":
            colls.append({
                "pattern": "verb + subject",
                "lemmas": [p_lemma, lemma],
                "idx": [p_idx, idx]
            })
        elif rel == "obj" and p_tag == "VERB":
            if prep:
                colls.append({
                    "pattern": "verb + prep + object",
                    "lemmas": [p_lemma, prep.data["lemma"], lemma],
                    "idx": [p_idx, prep.data["id"], idx]
                })
            else:
                colls.append({
                    "pattern": "verb + object",
                    "lemmas": [p_lemma, lemma],
                    "idx": [p_idx, idx]
                })
        if rel == "nmod" and p_tag == "NOUN":
            if prep:
                colls.append({
                    "pattern": "noun + prep + noun2",
                    "lemmas": [p_lemma, prep.data["lemma"], lemma],
                    "idx": [p_idx, prep.data["id"], idx]
                })
            else:
                colls.append({
                    "pattern": "mudaf_ileh + mudaf",
                    "lemmas": [p_lemma, lemma],
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
    collocations = db.get_collection("collocations")
    # Index for counting collocations
    collocations.create_index([("pattern", pymongo.ASCENDING), ("lemma", pymongo.ASCENDING)], unique=True)
    # Index for retrieving collocations
    collocations.create_index("lemmas")

    logging.info("Importing corpus %s into db ...", args.corpus)
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
            for c in s["collocations"]:
                # FIXME: Very bad design?!
                collocations.update_one({"pattern": c["pattern"], "lemma": " ".join(c["lemmas"])},
                                        {"$push": {"instances": _id}, "$set": { "lemmas": c["lemmas"] } },
                                        upsert=True)

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
