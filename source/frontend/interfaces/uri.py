from instance_manager import NavitiaManager 
import re

class InvalidUriException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class Uri:
    uri = None
    region_or_coord_part = None
    params = None
    region_ = None
    lon = None
    lat = None
    objects = []
    

    def __init__(self, string):
        self.uri = string
        self.parse_region_coord()
        self.parse_params()

    def region(self):
        if not self.region_ and self.lon and self.lat:
            #On va chercher la region associee
            self.region_ = NavitiaManager.key_of_coord(self.lon, self.lat)
            if not self.region_:
                raise InvalidUriException("No region is covering these coordinates")
        return self.region_


    def parse_region_coord(self):
        #On caste la premiere partie de l'url qui est soit une region, soit une
        #coordonnee (coord/lon;lat)
        a = re.compile("^(/)?(?P<firstpart>((?P<region>(?!coord/)\w+)|(coord/(?P<lon>([+-]?\d{0,2}\.?\d*));(?P<lat>([+-]?\d{1,2}\.?\d*)))))")
        m = a.search(self.uri)
        #Si on a trouve une premiere partie valide
        if(m.group("firstpart")):
            self.region_or_coord_part = self.uri[:m.end("firstpart")]
            self.params = self.uri[m.end("firstpart"):]
            #Dans le cas ou il s'agit d'une region
            if(m.group("region")):
                self.region_ = m.group("region")
            else:
                #Si c'est une coordonnee
                self.lon = float(m.group("lon"))
                self.lat = float(m.group("lat"))
            
    def parse_params(self):
        s =  self.params.split("/") 
        resource_type, uid = None, None
        for par in s:
            if par != "":
                if not resource_type:
                    if self.valid_resource_type(par):
                        resource_type = par
                    else:
                        raise InvalidUriException("Invalid resource type : "+par)
                else: 
                    uid = par
                    self.objects.append((resource_type, uid))
                    resource_type, uid = None, None
        if resource_type:
            self.objects.append((resource_type, uid))


    def valid_resource_type(self, resource_type):
        resource_types = ["connections", "stop_points", "networks",
        "commercial_modes", "physical_modes", "companies", "stop_areas",
        "routes", "lines"]

        return resource_type in resource_types


import unittest

class Tests(unittest.TestCase):
    def testOnlyRegionWithoutBeginningSlash(self):
        string = "paris"
        uri = Uri(string)
        self.assertEqual(uri.region(), "paris")

    def testOnlyRegionWithBeginningSlash(self):
        string = "/paris"
        uri = Uri(string)
        self.assertEqual(uri.region(), "paris")

    def testOnlyCoordPosWithoutSlash(self):
        string = "coord/1.1;2.3"
        uri = Uri(string)
        self.assertEqual(uri.lon, 1.1)
        self.assertEqual(uri.lat, 2.3)

        string = "coord/.1;2."
        uri = Uri(string)
        self.assertEqual(uri.lon, .1)
        self.assertEqual(uri.lat, 2)

        string = "coord/.111111;22.3"
        uri = Uri(string)
        self.assertEqual(uri.lon, .111111)
        self.assertEqual(uri.lat, 22.3)

    def testOnlyCoordPosWithSlash(self):
        string = "/coord/1.1;2.3"
        uri = Uri(string)
        self.assertEqual(uri.lon, 1.1)
        self.assertEqual(uri.lat, 2.3)

        string = "/coord/.1;2."
        uri = Uri(string)
        self.assertEqual(uri.lon, .1)
        self.assertEqual(uri.lat, 2)

        string = "/coord/.111111;22.3"
        uri = Uri(string)
        self.assertEqual(uri.lon, .111111)
        self.assertEqual(uri.lat, 22.3)
   
    def testResourceListWithslash(self):
        string = "/paris/stop_areas"
        uri = Uri(string)
        self.assertEqual(uri.region(), "paris")
        self.assertEqual(uri.params, "stop_areas")
        self.assertEqual(len(uri.objects), 1)
        self.assertEqual(uri.objects[0][0], "stop_areas")
        self.assertEqual(uri.objects[0][1], None)
   
    def testResourceWithslash(self):
        string = "/paris/stop_areas/1"
        uri = Uri(string)
        self.assertEqual(uri.region(), "paris")
        self.assertEqual(uri.params, "stop_areas")
        self.assertEqual(len(uri.objects), 1)
        self.assertEqual(uri.objects[0][0], "stop_areas")
        self.assertEqual(uri.objects[0][1], 1)
    
    def testResourceListWithoutSlash(self):
        string = "paris/stop_areas"
        uri = Uri(string)
        self.assertEqual(uri.region(), "paris")
        self.assertEqual(uri.params, "stop_areas")
        self.assertEqual(len(uri.objects), 1)
        self.assertEqual(uri.objects[0][0], "stop_areas")
        self.assertEqual(uri.objects[0][1], None)
   
    def testResourcetWithoutslash(self):
        string = "paris/stop_areas/1"
        uri = Uri(string)
        self.assertEqual(uri.region(), "paris")
        self.assertEqual(uri.params, "stop_areas")
        self.assertEqual(len(uri.objects), 1)
        self.assertEqual(uri.objects[0][0], "stop_areas")
        self.assertEqual(uri.objects[0][1], 1)