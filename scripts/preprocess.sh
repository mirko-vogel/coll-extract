#!/bin/bash
DIR=`dirname $0`
time java -jar "$DIR/segmenter/FarasaSegmenterJar.jar" --lemma yes  -i $1 > $1.lemmatized
time java -jar "$DIR/pos-tagger/FarasaPOSJar.jar" -i $1 -o $1.tagged 
$DIR/merge_farasa_lemma_pos.py $1.tagged $1.lemmatized > $1.merged

