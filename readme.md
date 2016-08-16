# caveman

using Stanford's CoreNLP tools to get a simplification of a sentence

# installation

instructions for myself on how to install corenlp tools

* Download [CoreNLP tools](http://stanfordnlp.github.io/CoreNLP/download.html)
* Extract to wherever, symlink to that folder for extra easiness

		ln -s stanford-corenlp-full-2015-12-09 corenlp

# usage

In the corenlp directory:

	java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer

Or

	./serve

this will start a server on port 9000 and run a demo in the browser at [http://localhost:9000/](http://localhost:9000/)

Then, while the server is running, you can make calls to it.

	wget --post-data 'The quick brown fox jumped over the lazy dog.' 'localhost:9000/?properties={"tokenize.whitespace":"true","annotators":"tokenize,ssplit,pos,parse,depparse","outputFormat":"json"}' -O -

Or

	./parse "the sentence you want to parse"

(The optional second argument is the annotators. the default for the second argument is `"tokenize,ssplit,pos,parse,depparse"`)

And then to do some re-munging of the sentence to create the caveman version,

	./caveman.py "the sentence you want to parse"
