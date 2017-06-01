
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

from __future__ import absolute_import, print_function, unicode_literals, division

import datetime
import pytz

from jormungandr.interfaces.v1.serializer import pt
from jormungandr.interfaces.v1.serializer.base import NullableDictSerializer, LambdaField
from jormungandr.interfaces.v1.serializer.fields import ErrorSerializer, FeedPublisherSerializer, PaginationSerializer
import serpy

from jormungandr.interfaces.v1.serializer.jsonschema.fields import Field
from jormungandr.interfaces.v1.serializer.time import DateTimeField, DateTimeDictField


class PTReferentialSerializer(serpy.Serializer):
    pagination = PaginationSerializer(attr='pagination', display_none=True, required=True)
    error = ErrorSerializer(display_none=False)
    feed_publishers = FeedPublisherSerializer(many=True, display_none=True)
    disruptions = pt.DisruptionSerializer(attr='impacts', many=True, display_none=True)


class LinesSerializer(PTReferentialSerializer):
    lines = pt.LineSerializer(many=True)


class DisruptionsSerializer(PTReferentialSerializer):
    #we already have a disruptions fields by default
    pass


class VehicleJourneysSerializer(PTReferentialSerializer):
    vehicle_journeys = pt.VehicleJourneySerializer(many=True)


class TripsSerializer(PTReferentialSerializer):
    trips = pt.TripSerializer(many=True)


class JourneyPatternsSerializer(PTReferentialSerializer):
    journey_patterns = pt.JourneyPatternSerializer(many=True)


class JourneyPatternPointsSerializer(PTReferentialSerializer):
    journey_pattern_points = pt.JourneyPatternPointSerializer(many=True)


class CommercialModesSerializer(PTReferentialSerializer):
    commercial_modes = pt.CommercialModeSerializer(many=True)


class PhysicalModesSerializer(PTReferentialSerializer):
    physical_modes = pt.PhysicalModeSerializer(many=True)


class StopPointsSerializer(PTReferentialSerializer):
    stop_points = pt.StopPointSerializer(many=True)


class StopAreasSerializer(PTReferentialSerializer):
    stop_areas = pt.StopAreaSerializer(many=True)


class RoutesSerializer(PTReferentialSerializer):
    routes = pt.RouteSerializer(many=True)


class LineGroupsSerializer(PTReferentialSerializer):
    line_groups = pt.LineGroupSerializer(many=True)


class NetworksSerializer(PTReferentialSerializer):
    networks = pt.NetworkSerializer(many=True)


class PlacesSerializer(serpy.Serializer):
    error = ErrorSerializer(display_none=False)
    feed_publishers = FeedPublisherSerializer(many=True, display_none=True)
    disruptions = pt.DisruptionSerializer(attr='impacts', many=True, display_none=True)
    places = pt.PlaceSerializer(many=True)


class CoverageErrorSerializer(NullableDictSerializer):
    code = Field(schema_type=str)
    value = Field(schema_type=str)


class CoverageDateTimeField(DateTimeDictField):
    """
    custom date time field for coverage, uses the coverage's timezone to format the date
    """
    def __init__(self, field_name=None, **kwargs):
        super(CoverageDateTimeField, self).__init__(**kwargs)
        self.field_name = field_name

    def to_value(self, coverage):
        tz_name = coverage.get('timezone')
        field_value = coverage.get(self.field_name)
        if not tz_name or not field_value:
            return None
        dt = datetime.datetime.utcfromtimestamp(field_value)
        tz = pytz.timezone(tz_name)
        if not tz:
            return None
        dt = pytz.utc.localize(dt)
        dt = dt.astimezone(tz)
        return dt.strftime("%Y%m%dT%H%M%S")


class CoverageSerializer(NullableDictSerializer):
    id = Field(attr="region_id", schema_type=str, description='Identifier of the coverage')
    start_production_date = Field(schema_type=str, description='Beginning of the production period. '
                                                               'We only have data on this production period')
    end_production_date = Field(schema_type=str, description='End of the production period. '
                                                             'We only have data on this production period')
    last_load_at = LambdaField(method=lambda _, o: CoverageDateTimeField('last_load_at').to_value(o),
                               description='Datetime of the last data loading',
                               schema_type=str)
    name = Field(schema_type=str, description='Name of the coverage')
    status = Field(schema_type=str)
    shape = Field(schema_type=str, description='GeoJSON of the shape of the coverage')
    error = CoverageErrorSerializer(display_none=False)
    dataset_created_at = Field(schema_type=str, description='Creation date of the dataset')


class CoveragesSerializer(serpy.DictSerializer):
    regions = CoverageSerializer(many=True)
