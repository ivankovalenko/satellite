import json
import math

from twisted.web import server, resource
from twisted.web.server import NOT_DONE_YET
from twisted.web.client import Agent, readBody
from twisted.internet import reactor, endpoints, defer
from twisted.internet.defer import inlineCallbacks, returnValue

class MainResource(resource.Resource):
    isLeaf = True

    url = 'http://www.n2yo.com/sat/instant-tracking.php'
    url_info = 'http://www.n2yo.com/sat/jtest.php'

    def parse_pos_string(self, pos_string):
        l = pos_string.split('|')
        l = map(lambda v: float(v), l[:7])
        return {
            'lat': l[0],
            'lon': l[1],
            'azimuth': l[2],
            'elevation': l[3],
            'altitude': l[6],
            'speed': math.sqrt(398600.8 / (l[6] + 6378.135)),
        }

    def parse_pos_list(self, pos_list):
        return self.parse_pos_string(pos_list[0]['d'])
    
    def get_geometry(self, parsed_pos):
        return {"type": "Point", "coordinates": [parsed_pos.pop('lon'), parsed_pos.pop('lat'), parsed_pos['altitude']*1000]}

    def get_properties(self, parsed_pos):
        return parsed_pos

    def create_geojson(self, data, info):
        geojson_data = {
            "type": "FeatureCollection",
            "features": []
        }
        for i in data:
            sat_id = i.get('id')
            feature = {
              "type": "Feature",
              "sat_id": sat_id,
              "properties": {},
              "geometry": None,
            }
            pos_list = i.get('pos')
            if pos_list:
                parsed_pos = self.parse_pos_list(pos_list)
                feature['geometry'] = self.get_geometry(parsed_pos)
                feature['properties'] = self.get_properties(parsed_pos)
                sat_info = info.get(sat_id)
                if sat_info:
                    feature['properties'].update({
                        'sat_name': sat_info.get('name'),
                        'int_designator': sat_info.get('int_designator'),
                        'period': sat_info.get('period'),
                    })
                
            geojson_data['features'].append(feature)
        return json.dumps(geojson_data)

    @inlineCallbacks
    def get_info(self, s):
        url = '%s?d=1&s=%s' % (self.url_info, s)
        agent = Agent(reactor)
        resp = yield agent.request('GET', url)
        body = yield readBody(resp)
        info = {}
        for sat in json.loads(body):
            sat.pop('pos')
            info[sat['id']] = sat
        returnValue(info)

    @inlineCallbacks
    def get_coords(self, s, d=1):
        url = '%s?d=%s&s=%s' % (self.url, d, s)
        agent = Agent(reactor)
        resp = yield agent.request('GET', url)
        body = yield readBody(resp)
        coords = json.loads(body)
        returnValue(coords)

    @inlineCallbacks
    def get_data(self, s):
        info, coords = yield defer.gatherResults([self.get_info(s), self.get_coords(s)])
        geojson = self.create_geojson(coords, info)
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

class OrbitResource(MainResource):
    isLeaf = True
    
    @inlineCallbacks
    def get_info_with_coords(self, s):
        url = '%s?s=%s' % (self.url_info, s)
        agent = Agent(reactor)
        resp = yield agent.request('GET', url)
        body = yield readBody(resp)
        info = {}
        for sat in json.loads(body):
            info[sat['id']] = sat
        returnValue(info)
    
    @inlineCallbacks
    def get_orb_data(self, s):
        info = yield self.get_info_with_coords(s)
        coords = [{'id': k, 'pos': v.pop('pos')} for k, v in info.items()]
        geojson = self.create_geojson(coords, info)
        returnValue(geojson)
        
    @inlineCallbacks
    def get_step_orb_data(self, s, d, p):
        info = yield self.get_info(s)
        d = d or max([int(i['period']) for i in info.values()])
        coords = yield self.get_coords(s, d)
        
        if p > 1:
            for c in coords:
                c['pos'] = [i for i in c['pos'][::p]]
                
        geojson = self.create_geojson(coords, info)
        returnValue(geojson)
    
    def parse_pos_list(self, pos_list):
        return [self.parse_pos_string(pos['d']) for pos in pos_list]
    
    def parse_pos_string(self, pos_string):
        l = pos_string.split('|')
        l = map(lambda v: float(v), l[:7])
        return {
            'lat': l[0],
            'lon': l[1],
            'altitude': l[2],
        }
        
    def get_geometry(self, parsed_pos):
        coords = [(pos.pop('lon'), pos.pop('lat'), pos['altitude']*1000) for pos in parsed_pos]
        return {"type": "LineString", "coordinates": coords}
    
    def get_properties(self, parsed_pos):
        return dict()
    
    @inlineCallbacks
    def defer_GET(self, request):
        s = request.args.get('s')
        if not s:
            request.setResponseCode(400)
            request.finish()
            returnValue(0)
        p = request.args.get('p')
        d = request.args.get('d')
        if d or p:
            p = int(p[0]) if p else 1
            d = d[0] if d else 0 
            resp = yield self.get_step_orb_data(s[0], d, p)
        else:
            resp = yield self.get_orb_data(s[0])
        request.setHeader("content-type", "application/json")
        request.setHeader("Access-Control-Allow-Origin", "*")
        request.write(resp)
        request.finish()
    

root = resource.Resource()
root.putChild('', MainResource())
root.putChild('orbit', OrbitResource())
endpoints.serverFromString(reactor, "tcp:8080").listen(server.Site(root))
reactor.run()
