#!/usr/bin/python

import requests
import sys
import json

import re

def parse(textToParse):
	annotators = "tokenize,ssplit,pos,parse,depparse,coref"

	serverURL = "http://localhost:9000/"
	serverProperties = '?properties={"annotators":"' + annotators + '","outputFormat":"json"}'

	r = requests.post(
		serverURL + serverProperties,
		data = textToParse
	)

	return json.loads(r.text)

def collectNPsForCoreferredEntity(coref, c):
	nps = []
	for mention in coref:
		pronoun = mention["type"]=="PRONOMINAL"
		representative = mention["isRepresentativeMention"]
		if representative and not pronoun:
			nps.append(mention)
	return nps

def fixIndex(index):
	return index-1

def breakIndex(index):
	return index+1

def lemma(t, caveman=True):
	if caveman:
		if "coreferredEntityLabel" in t:
			return t["coreferredEntityLabel"]
		if t["lemma"] in ["I", "he", "she"]:
			return {
				"I": "me", "he": "him", "she": "her"
			}[t["lemma"]]
	return t["lemma"]

def word(t):
	return t["word"]

def words(lst):
	return map(word, lst)

def lemmas(lst, caveman=True):
	return map(lambda t: lemma(t, caveman), lst)

def getDependentsOf(index, dependencies, link=None):
	candidates = filter(
		lambda d: d["governor"]==breakIndex(index),
		dependencies
	)
	if link:
		candidates = filter(lambda d: d["dep"]==link, candidates)
	return map(
		lambda d: fixIndex(d["dependent"]),
		candidates
	)

def searchDependencyLayer(roots, startIndex, endIndex, sentence):
	tokens = sentence["tokens"]
	dependencies = sentence["basic-dependencies"]
	newRoots = []
	for root in roots:
		topLayerDeps = getDependentsOf(root, dependencies)
		for dIndex in topLayerDeps:
			if startIndex <= dIndex and dIndex < endIndex:
				return lemma(tokens[dIndex])
			else:
				newRoots.append(dIndex)
	return searchDependencyLayer(newRoots, startIndex, endIndex, sentence)

def phraseHead(startIndex, endIndex, sentence):
	tokens = sentence["tokens"]
	phrase = tokens[startIndex:endIndex]
	if len(phrase)==1:
		return lemma(phrase[0])
	else:
		return searchDependencyLayer([-1], startIndex, endIndex, sentence)
	print "error 2039: didn't get a phrase head for:",
	print " ".join(lemmas(phrase))
	stop

def collectPhraseWords(mention, sentences):
	sentNum = fixIndex(mention["sentNum"])
	startIndex = fixIndex(mention["startIndex"])
	endIndex = fixIndex(mention["endIndex"])
	sentence = sentences[sentNum]
	return phraseHead(startIndex, endIndex, sentence)

def chooseLabelForEntity(coref, sentences, c):
	nps = collectNPsForCoreferredEntity(coref, c)
	if len(nps)!=0:
		phraseHeads = map(lambda np: collectPhraseWords(np, sentences), nps)
		if len(phraseHeads)!=1:
			print "error 2392: multiple phrases. not sure how to choose"
			stop
		return phraseHeads[0]

def incorporatenEntityLabel(label, coref, sentences):
	for mention in coref:
		sentNum = fixIndex(mention["sentNum"])
		startIndex = fixIndex(mention["startIndex"])
		endIndex = fixIndex(mention["endIndex"])
		for i in range(startIndex, endIndex):
			sentences[sentNum]['tokens'][i]["coreferredEntityLabel"] = label
	return sentences

def relabelCoreferredEntities(parsed):
	corefs = parsed["corefs"]
	sentences = parsed["sentences"]
	for c in corefs:
		coref = corefs[c]
		label = chooseLabelForEntity(coref, sentences, c)
		if label:
			sentences = incorporatenEntityLabel(label, coref, sentences)
	return sentences

def cleanup(string):
	string = re.sub(r" ([.?!,])", r"\1", string)
	return string

def printFullText(sentences):
	text = " ".join(map(lambda s: " ".join(words(s["tokens"])), sentences))
	return cleanup(text)

def hasDepLink(index, dependencies, link):
	deps = getDependentsOf(index, dependencies, link=link)
	return len(deps) > 0

def getMainPred(sentence):
	dependencies = sentence["basic-dependencies"]
	wordIndex = getDependentsOf(-1, dependencies, link="ROOT")[0]
	isPassive = hasDepLink(wordIndex, dependencies, "nsubjpass")
	token = sentence["tokens"][wordIndex]
	if isPassive:
		return word(token)
	else:
		return lemma(token)

def getSubject(sentence):
	dependencies = sentence["basic-dependencies"]
	predIndex = getDependentsOf(-1, dependencies, link="ROOT")[0]
	wordIndex = (getDependentsOf(predIndex, dependencies, "nsubj") + getDependentsOf(predIndex, dependencies, "nsubjpass"))[0]
	return lemma(sentence["tokens"][wordIndex])

def getObject(sentence):
	dependencies = sentence["basic-dependencies"]
	predIndex = getDependentsOf(-1, dependencies, link="ROOT")[0]
	possibleObjIndices = getDependentsOf(predIndex, dependencies, link="dobj")
	if len(possibleObjIndices) > 0:
		return lemma(sentence["tokens"][possibleObjIndices[0]])

def cavemanText(cavemanData):
	cavemanSentences = []
	for sentence in cavemanData["sentences"]:
		cavemanSentences.append(" ".join(filter(
			lambda x: x!=None,
			[
				sentence["subj"],
				sentence["pred"],
				sentence["dobj"],
				sentence["finalPunctuation"]
			]
		)))
	return {
		"full": " ".join(map(cleanup, cavemanSentences))
	}

def getFinalPunctuation(sentence):
	finalToken = word(sentence["tokens"][-1])
	if finalToken in ["?"]:
		return "?"
	return "."

def collectCavemanComponents(cavemanData, sentences):
	# girl not think boy not give banana monkey
	cavemanData["sentences"] = []
	for sentence in sentences:
		sentenceData = {}
		sentenceData["pred"] = getMainPred(sentence)
		sentenceData["subj"] = getSubject(sentence)
		sentenceData["dobj"] = getObject(sentence)
		sentenceData["finalPunctuation"] = getFinalPunctuation(sentence)
		cavemanData["sentences"].append(sentenceData)
	cavemanData["caveman"] = cavemanText(cavemanData)
	return cavemanData

def caveman(textToParse):
	# replace pronouns with resolved lemmas if possible
	parsed = parse(textToParse)
	sentences = relabelCoreferredEntities(parsed)
	cavemanData = {
		"text": printFullText(sentences),
	}
	cavemanData = collectCavemanComponents(cavemanData, sentences)
	print cavemanData

caveman(sys.argv[1])