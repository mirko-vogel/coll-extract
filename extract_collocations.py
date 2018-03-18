#!/usr/bin/python
# coding=utf-8
import json
import argparse
import logging
from pymongo import MongoClient

from extraction import Pattern, PatternExtractor

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("corpus", type=argparse.FileType(),
                   help="Path to the manatee corpus registry file")
    p.add_argument("core", type=str, nargs="+",
                   help="The cores (lemmas) to extract collocations for")
    p.add_argument("--debug", action="store_true",
                   help="Log debug messages")

    g = p.add_argument_group("Pattern parameters")
    p.add_argument("--pattern", type=str,
                   help="Pattern to extract collocations for")
    p.add_argument("--asterix", type=str, default="[]{0,}",
                   help="Representation of * in CQL")
    p.add_argument("--within", type=str, default="s",
                   help="Limit patterns to match within given structure")

    g = p.add_argument_group("Example selection parameters")
    g.add_argument("--example-count", type=int, default=10,
                   help="Number of examples to fetch for each candidate.")

    g = p.add_argument_group("Candidate filter parameters")
    g.add_argument("--min-freq", type=int, default=0,
                   help="Drop candidates if freq is below min_freq")
    g.add_argument("--min-score", type=int, default=0,
                   help="Drop candidates if score is below min_score")

    g = p.add_argument_group("Storage parameters")
    g.add_argument("--write-to-file", type=argparse.FileType("w"), dest="out_file",
                   help="Write extracted collocatons to given file (default, write to mongodb)")
    g.add_argument("--db-url", type=str)
    g.add_argument("--db-name", type=str, default="collocation_review")
    g.add_argument("--db-collection", type=str, default="candidates")

    args = p.parse_args()
    cores = [s.decode("utf-8").split(" ") for s in args.core]
    p = Pattern(args.pattern, args.asterix, args.within)

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Extracting collocations (pattern '%s') for the following cores: %s",
                 unicode(p), ", ".join(" ".join(c) for c in cores))

    if args.out_file:
        logging.info("Extracted collocations will be written to '%s'.", args.out_file.name)
    else:
        logging.info("Extracted collocations will be written to MongoDB (%s, %s.%s).",
                     args.db_url, args.db_name, args.db_collection)
        db = MongoClient(args.db_url).get_database(args.db_name).get_collection(args.db_collection)

    result = []
    e = PatternExtractor(args.corpus.name, p)
    for core in cores:
        logging.info("Extracting collocations for '%s' ...", " ".join(core))
        candidates = e.fetch_candidates(core)

        logging.info("Filtering candidates ...")
        candidates = [c for c in candidates
                      if c.freq >= args.min_freq
                      and  set(c.lemma).isdisjoint(u"\"'.,،-()[]{}")]
        logging.info("Done. %d candidates (%d instances) remaining.",
                     len(candidates), sum(c.freq for c in candidates))

        logging.info("Getting %d examples and marginal counts for each candidate ...", args.example_count)
        for c in candidates:
            c.fetch_marginal_count()
            c.fetch_examples(["word", "fullpos"], args.example_count)
            result.append(c.get_as_json())

        logging.info("Done.")

    logging.info("Extracting finished, saving candidates ...")
    if args.out_file:
        json.dump(result, args.out_file, indent=2, ensure_ascii=False, encoding="utf-8")
    else:
        db.insert_many(result)
    logging.info("Done.")
