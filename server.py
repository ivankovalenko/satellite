import json
import math

from twisted.web import server, resource
from twisted.web.server import NOT_DONE_YET
from twisted.web.client import Agent, readBody
from twisted.internet import reactor, endpoints
from twisted.internet.defer import inlineCallbacks, returnValue

class MainResource(resource.Resource):
    isLeaf = True

    url = 'http://www.n2yo.com/sat/instant-tracking.php'

    def parse_pos_string(self, pos_string):
        l = pos_string.split('|')
        return {
            'lat': l[0],
            'lon': l[1],
            'azimuth': l[2],
            'elevation': l[3],
            'altitude': l[6],
            'speed': math.sqrt(398600.8 / (float(l[6]) + 6378.135)),
        }

    def create_geojson(self, data):
        data = json.loads(data)
        geojson_data = {
            "type": "FeatureCollection",
            "features": []
        }
        for i in data:
            feature = {
              "type": "Feature",
              "id": i.get('id'),
              "properties": {},
              "geometry": None,
            }
            pos_list = i.get('pos')
            if pos_list:
                pos = self.parse_pos_string(pos_list[0]['d'])
                feature['geometry'] = {"type": "Point", "coordinates": [pos.pop('lon'), pos.pop('lat')]}
                feature['properties'] = pos
            geojson_data['features'].append(feature)
        return json.dumps(geojson_data)

    @inlineCallbacks
    def get_coords(self, s):
        url = '%s?d=1&s=%s' % (self.url, s)
        agent = Agent(reactor)
        resp = yield agent.request('GET', url)
        body = yield readBody(resp)
        returnValue(body)

    @inlineCallbacks
    def get_data(self, s):
        coords = yield self.get_coords(s)
        geojson = self.create_geojson(coords)
        returnValue(geojson)
        
    @inlineCallbacks
    def defer_GET(self, request):
        s = request.args.get('s')
        if not s:
            request.setResponseCode(400)
            request.finish()
            returnValue(0)
        resp = yield self.get_data(s[0])
        request.setHeader("content-type", "application/json")
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(resp)
        request.finish()

    def render_GET(self, request):
        reactor.callLater(0, self.defer_GET, request)
        return NOT_DONE_YET

endpoints.serverFromString(reactor, "tcp:80").listen(server.Site(MainResource()))
reactor.run()
