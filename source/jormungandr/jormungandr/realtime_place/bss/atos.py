# Copyright (c) 2001-2014, Canal TP and/or its affiliates. All rights reserved.
#
# This file is part of Navitia,
#     the software to build cool stuff with public transport.
#
# Hope you'll enjoy and contribute to this project,
#     powered by Canal TP (www.canaltp.fr).
# Help us simplify mobility and open public transport:
#     a non ending quest to the responsive locomotion way of traveling!
#
# LICENCE: This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Stay tuned using
# twitter @navitia
# IRC #navitia on freenode
# https://groups.google.com/d/forum/navitia
# www.navitia.io
from bss_provider import BssProvider
from stands import Stands
import suds


class AtosProvider(BssProvider):

    WS_URL_TEMPLATE = 'https://{}.velossimo.com/services/terminal?wsdl'
    OPERATOR = 'Keolis'

    def __init__(self, id_ao, network, subdomain='admin'):
        self.id_ao = id_ao
        self.network = network
        self.WS_URL = self.WS_URL_TEMPLATE.format(subdomain)

    def support_poi(self, poi):
        properties = poi.get('properties', {})
        return properties.get('operator', '') == self.OPERATOR and \
               properties.get('network', '').encode('utf-8') == self.network

    def get_informations(self, poi):
        try:
            all_stands = self.get_all_stands()
            ref = poi.get('properties', {}).get('ref', '')
            stands = all_stands.get(ref)
            if stands:
                return stands
        except Exception:
            pass
        return None

    def get_all_stands(self):
        client = self.get_client()
        all_stands = client.service.getSummaryInformationTerminals(self.id_ao)
        result = {}
        for stands in all_stands:
            result[stands.libelle] = Stands(stands.nbPlacesDispo, stands.nbVelosDispo)
        return result

    def get_client(self):
        return suds.client.Client(self.WS_URL, cache=None)
