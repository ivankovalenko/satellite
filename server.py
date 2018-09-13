import json
import math

from twisted.web import server, resource
from twisted.web.server import NOT_DONE_YET
from twisted.web.client import Agent, readBody
from twisted.internet import reactor, endpoints, defer
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.logger import Logger

log = Logger()

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

    def create_geojson(self, data, info, **kwargs):
        geojson_data = {
            "type": "FeatureCollection",
            "features": []
        }
        for i in data:
            sat_id = i.get('id')
            feature = {
              "type": "Feature",
              "sat_id": sat_id,
              "id": sat_id,
              "properties": {},
              "geometry": None,
            }
            pos_list = i.get('pos')
            if pos_list:
                parsed_pos = self.parse_pos_list(pos_list, **kwargs)
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
        log.info(body)
#        for sat in json.loads(body):
#            sat.pop('pos')
#            info[sat['id']] = sat
#        returnValue(info)

    @inlineCallbacks
    def get_coords(self, s, d=1):
        url = '%s?d=%s&s=%s' % (self.url, d, s)
        agent = Agent(reactor)
        resp = yield agent.request('GET', url)
        body = yield readBody(resp)
        log.info(body)
#        coords = json.loads(body)
#        returnValue(coords)

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
        log.info(body)
#        for sat in json.loads(body):
#            info[sat['id']] = sat
#        returnValue(info)
    
    @inlineCallbacks
    def get_orb_data(self, s):
        info = yield self.get_info_with_coords(s)
        coords = [{'id': k, 'pos': v.pop('pos')} for k, v in info.items()]
        
        # Cut passed orbit. About 1/3 first points.
        for coord in coords:
            num_point = len(coord['pos']) / 3
            coord['pos'] = coord['pos'][num_point:]
        
        geojson = self.create_geojson(coords, info, altitude_index=2)
        returnValue(geojson)
        
    @inlineCallbacks
    def get_step_orb_data(self, s, d, p):
        info = yield self.get_info(s)
        d = d or max([int(i['period']) for i in info.values()])
        coords = yield self.get_coords(s, d)
        
        if p > 1:
            for c in coords:
                c['pos'] = [i for i in c['pos'][::p]]
                
        geojson = self.create_geojson(coords, info, altitude_index=6)
        returnValue(geojson)
    
    def parse_pos_list(self, pos_list, altitude_index, **kwargs):
        return [self.parse_pos_string(pos['d'], altitude_index) for pos in pos_list]
    
    def parse_pos_string(self, pos_string, altitude_index=6):
        l = pos_string.split('|')
        l = map(lambda v: float(v), l[:7])
        return {
            'lat': l[0],
            'lon': l[1],
            'altitude': l[altitude_index],
        }
        
    def get_geometry(self, parsed_pos):
        coords = [(pos.pop('lon'), pos.pop('lat'), pos['altitude']*1000) for pos in parsed_pos]
        is_positive = coords[0][0] > 0
        lines = []
        j = 0
        for i, c in enumerate(coords):
            # For True case both values must be the same
            if not ((c[0] > 0) ^ is_positive):
                continue
            is_positive = not is_positive 
            # <90 because need only catch changed sign near -180 and 180 lon
            if abs(c[0]) < 90:
                continue
            lines.append(coords[j:i])
            j = i
        else:
            lines.append(coords[j:])
            
        def calc_lat(first_point, second_point):
            a = first_point[0] - second_point[0]
            b = first_point[1] - second_point[1]
            tga = a/b
            if first_point[0] > 0:
                a1 = 180 - first_point[0]
            else:
                a1 = -180 - first_point[0]
            return a1/tga
        
        for line in lines:
            start_lon = 180 if line[0][0] > 0 else -180
            end_lon = 180 if line[-1][0] > 0 else -180
                
            start_lat_diff = calc_lat(line[0], line[1])
            end_lat_diff = calc_lat(line[-1], line[-2])
            
            start_lat = line[0][1] + start_lat_diff
            end_lat = line[-1][1] + end_lat_diff
                 
            line.insert(0, (start_lon, start_lat, line[0][2]))
            line.append((end_lon, end_lat, line[-1][2]))
        
        lines[0].pop(0)
        lines[-1].pop()
        
        return {"type": "MultiLineString", "coordinates": lines}
    
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
endpoints.serverFromString(reactor, "tcp:80").listen(server.Site(root))
reactor.run()
