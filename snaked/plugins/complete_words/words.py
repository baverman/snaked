from threading import Thread
import re

words = {}
current_jobs = {}
matcher = re.compile(r'[\w-]{3,}')

def process(filename, data):
    result = {}
    
    for w in matcher.findall(data):
        try:
            result[w] += 1
        except KeyError:
            result[w] = 1

    for w, c in result.iteritems():
        words.setdefault(w, {})[filename] = c
    
    for w in [w for w, files in words.iteritems() if w not in result and filename in files]:
        del words[w][filename]

def add_job(filename, data):
    if filename in current_jobs:
        current_jobs[filename].join()

    thread = Thread(target=process, args=(filename, data))
    current_jobs[filename] = thread
    thread.start()
    