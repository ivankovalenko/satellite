import json
import math

from twisted.web import server, resource
from twisted.web.server import NOT_DONE_YET
from twisted.web.client import Agent, readBody
from twisted.internet import reactor, endpoints, defer
from twisted.internet.defer import inlineCallbacks, returnValue

# Create your tests here.
def main():
    url = 'http://www.n2yo.com/sat/instant-tracking.php'
    url_info = 'http://www.n2yo.com/sat/jtest.php'

    url = '%s?d=%s&s=%s' % (url, 1, 25544)
    print (url)

    agent = Agent(reactor)
    resp = yield agent.request('GET', url)
#    body = yield readBody(resp)
#    coords = json.loads(body.translate(None, '\n\t\r'))
    
#    print (coords)

main()