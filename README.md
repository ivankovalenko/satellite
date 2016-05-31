# Description

Web service return information about the satellites location and parameters. The service uses data from http://www.n2yo.com/ and returns geoJSON with location and satellite attributes of a given satellite.

Available satellites list http://www.n2yo.com/satellites/ 

![Screenshot from 2016-05-31 13-12-42.png](https://bitbucket.org/repo/qq8xLk/images/4188823746-Screenshot%20from%202016-05-31%2013-12-42.png)

# How to use this image

## Run a satellite tracking instance

```
#!bash

$ docker run --name satellite_tracking -d --restart=always mediagis/satellite-tracking
```
Service will run at http://localhost:80


# Request examples


## Information about satellites

```
http://localhost/?s=25544|28931
```
This request return information about `SPACE STATION` and `ALOS`.

**Response:**

```
#!json

{
  type: "FeatureCollection",
  features: [
    {
      geometry: {
        type: "Point",
        coordinates: [
          -87.09654781,
          22.84623564,
          402420
        ]
      },
      sat_id: "25544",
      type: "Feature",
      id: "25544",
      properties: {
        elevation: -41.84,
        altitude: 402.42,
        period: "5580",
        sat_name: "SPACE STATION",
        azimuth: 292.74,
        speed: 7.667194164014538,
        int_designator: "1998-067A"
      }
    },
    {
      geometry: {
        type: "Point",
        coordinates: [
          155.518122,
          40.93693575,
          690740
        ]
      },
      sat_id: "28931",
      type: "Feature",
      id: "28931",
      properties: {
        elevation: -65.54,
        altitude: 690.74,
        period: "5940",
        sat_name: "ALOS",
        azimuth: 25.67,
        speed: 7.509204504294438,
        int_designator: "2006-002A"
      }
    }
  ]
}
```

## Information about satellites orbit

```
http://localhost/orbit/?s=25544|28931
```

**Response:**

```
#!json

{
  type: "FeatureCollection",
  features: [
    {
      geometry: {
        type: "MultiLineString",
        coordinates: [
          [
            -27.2129558,
            -42.58658788,
            417360
          ],
          [
            ...
          ]
        ]
      },
      sat_id: "25544",
      type: "Feature",
      id: "25544",
      properties: {
        sat_name: "SPACE STATION",
        int_designator: "1998-067A",
        period: "5580"
      }
    },
    {
      geometry: {
        type: "MultiLineString",
        coordinates: [
          [
            -12.22710724,
            54.43303266,
            693780
          ],
          [
            ...
          ]
        ]
      },
      sat_id: "28931",
      type: "Feature",
      id: "28931",
      properties: {
        sat_name: "ALOS",
        int_designator: "2006-002A",
        period: "5940"
      }
    }
  ]
}
```