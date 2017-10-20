# coding=utf-8

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

from __future__ import absolute_import, print_function, unicode_literals, division
from flask_restful import fields, marshal_with, reqparse
from flask import request, g
from jormungandr import i_manager, utils
from jormungandr import timezone
from jormungandr.interfaces.v1.fields import stop_point, route, pagination, PbField, stop_date_time, \
    additional_informations, stop_time_properties_links, display_informations_vj, \
    display_informations_route, UrisToLinks, error, \
    enum_type, SplitDateTime, MultiLineString, PbEnum, feed_publisher, DateTime
from jormungandr.interfaces.v1.ResourceUri import ResourceUri, complete_links
from jormungandr.interfaces.v1.decorators import get_obj_serializer
from jormungandr.interfaces.v1.serializer import api, pt
from datetime import datetime, timedelta
from jormungandr.interfaces.argument import ArgumentDoc
from jormungandr.interfaces.parsers import DateTimeFormat, default_count_arg_type, depth_argument, \
    UnsignedInteger
from jormungandr.interfaces.v1.errors import ManageError
from flask_restful.inputs import natural
from jormungandr.interfaces.v1.fields import disruption_marshaller, NonNullList, NonNullNested
from jormungandr.resources_utils import ResourceUtc
from jormungandr.interfaces.v1.make_links import create_external_link, create_internal_link
from functools import wraps
from copy import deepcopy
from navitiacommon import response_pb2
from jormungandr.exceptions import InvalidArguments
import six
from navitiacommon.parser_args_type import BooleanType, OptionValue


class Schedules(ResourceUri, ResourceUtc):

    def __init__(self, endpoint, *args, **kwargs):
        ResourceUri.__init__(self, *args, **kwargs)
        ResourceUtc.__init__(self)
        self.endpoint = endpoint
        self.parsers["get"] = reqparse.RequestParser(argument_class=ArgumentDoc)
        parser_get = self.parsers["get"]
        parser_get.add_argument("filter", type=six.text_type)
        parser_get.add_argument("from_datetime", type=DateTimeFormat(), default=None,
                                help="The datetime from which you want the schedules")
        parser_get.add_argument("until_datetime", type=DateTimeFormat(), default=None,
                                help="The datetime until which you want the schedules")
        parser_get.add_argument("duration", type=int, default=3600 * 24,
                                help="Maximum duration between datetime and the retrieved stop time")
        parser_get.add_argument("depth", type=depth_argument, default=2)
        parser_get.add_argument("count", type=default_count_arg_type, default=10,
                                help="Number of schedules per page")
        parser_get.add_argument("start_page", type=int, default=0,
                                help="The current page")
        parser_get.add_argument("max_date_times", type=UnsignedInteger(), deprecated=True,
                                help="DEPRECATED, replaced by `items_per_schedule`")
        parser_get.add_argument("forbidden_id[]", type=six.text_type, deprecated=True,
                                help="DEPRECATED, replaced by `forbidden_uris[]`",
                                dest="__temporary_forbidden_id[]",
                                default=[],
                                action='append',
                                schema_metadata={'format': 'pt-object'})
        parser_get.add_argument("forbidden_uris[]", type=six.text_type,
                                help="forbidden uris",
                                dest="forbidden_uris[]",
                                default=[],
                                action='append',
                                schema_metadata={'format': 'pt-object'})
        parser_get.add_argument("calendar", type=six.text_type,
                                help="Id of the calendar")
        parser_get.add_argument("distance", type=int, default=200,
                                help="Distance range of the query. Used only if a coord is in the query")
        parser_get.add_argument("show_codes", type=BooleanType(), default=False,
                                help="show more identification codes")
        #Note: no default param for data freshness, the default depends on the API
        parser_get.add_argument("data_freshness",
                                help='freshness of the data. '
                                     'base_schedule is the long term planned schedule. '
                                     'adapted_schedule is for planned ahead disruptions (strikes, '
                                     'maintenances, ...). '
                                     'realtime is to have the freshest possible data',
                                type=OptionValue(['base_schedule', 'adapted_schedule', 'realtime']))
        parser_get.add_argument("_current_datetime", type=DateTimeFormat(),
                                schema_metadata={'default': 'now'}, hidden=True,
                                default=datetime.utcnow(),
                                help='The datetime considered as "now". Used for debug, default is '
                                     'the moment of the request. It will mainly change the output '
                                     'of the disruptions.')
        parser_get.add_argument("items_per_schedule", type=UnsignedInteger(), default=10000,
                                help="maximum number of date_times per schedule")
        parser_get.add_argument("disable_geojson", type=BooleanType(), default=False,
                                help="remove geojson from the response")

        self.get_decorators.insert(0, ManageError())
        self.get_decorators.insert(1, get_obj_serializer(self))
        self.get_decorators.append(complete_links(self))

    def options(self, **kwargs):
        return self.api_description(**kwargs)

    def get(self, uri=None, region=None, lon=None, lat=None):
        args = self.parsers["get"].parse_args()

        # for retrocompatibility purpose
        for forbid_id in args['__temporary_forbidden_id[]']:
            args['forbidden_uris[]'].append(forbid_id)

        args["nb_stoptimes"] = args["count"]

        if args['disable_geojson']:
            g.disable_geojson = True

        # retrocompatibility
        if args['max_date_times'] is not None:
            args['items_per_schedule'] = args['max_date_times']

        if uri is None:
            if not args['filter']:
                raise InvalidArguments('filter')
            first_filter = args["filter"].lower().split("and")[0].strip()
            parts = first_filter.lower().split("=")
            if len(parts) != 2:
                error = "Unable to parse filter {filter}"
                return {"error": error.format(filter=args["filter"])}, 503
            else:
                self.region = i_manager.get_region(object_id=parts[1].strip())
        else:
            self.collection = 'schedules'
            args["filter"] = self.get_filter(uri.split("/"), args)
            self.region = i_manager.get_region(region, lon, lat)
        timezone.set_request_timezone(self.region)

        if not args["from_datetime"] and not args["until_datetime"]:
            # no datetime given, default is the current time, and we activate the realtime
            args['from_datetime'] = args['_current_datetime']
            if args["calendar"]:  # if we have a calendar, the dt is only used for sorting, so 00:00 is fine
                args['from_datetime'] = args['from_datetime'].replace(hour=0, minute=0)

            if not args['data_freshness']:
                args['data_freshness'] = 'realtime'
        elif not args.get('calendar'):
            #if a calendar is given all times will be given in local (because the calendar might span over dst)
            if args['from_datetime']:
                args['from_datetime'] = self.convert_to_utc(args['from_datetime'])
            if args['until_datetime']:
                args['until_datetime'] = self.convert_to_utc(args['until_datetime'])

        # we save the original datetime for debuging purpose
        args['original_datetime'] = args['from_datetime']
        if args['from_datetime']:
            args['from_datetime'] = utils.date_to_timestamp(args['from_datetime'])
        if args['until_datetime']:
            args['until_datetime'] = utils.date_to_timestamp(args['until_datetime'])

        if not args['data_freshness']:
            # The data freshness depends on the API
            # for route_schedule, by default we want the base schedule
            if self.endpoint == 'route_schedules':
                args['data_freshness'] = 'base_schedule'
            # for stop_schedule and previous/next departure/arrival, we want the freshest data by default
            else:
                args['data_freshness'] = 'realtime'

        if not args["from_datetime"] and args["until_datetime"]\
                and self.endpoint[:4] == "next":
            self.endpoint = "previous" + self.endpoint[4:]

        self._register_interpreted_parameters(args)
        return i_manager.dispatch(args, self.endpoint,
                                  instance_name=self.region)

class date_time_links(fields.Raw):

    def output(self, key, obj):
        disruption_links = [create_internal_link(_type="disruption", rel="disruptions", id=uri)
                            for uri in obj.impact_uris]
        properties_links = pt.make_properties_links(obj.properties)
        return properties_links + disruption_links


date_time = {
    "date_time": SplitDateTime(date='date', time='time'),
    "base_date_time": DateTime(),
    "additional_informations": additional_informations(),
    "links": date_time_links(),
    'data_freshness': enum_type(attribute='realtime_level'),
}

row = {
    "stop_point": PbField(stop_point),
    "date_times": fields.List(fields.Nested(date_time))
}

header = {
    "display_informations": PbField(display_informations_vj,
                                    attribute='pt_display_informations'),
    "additional_informations": NonNullList(PbEnum(response_pb2.SectionAdditionalInformationType)),
    "links": UrisToLinks()
}
table_field = {
    "rows": fields.List(fields.Nested(row)),
    "headers": fields.List(fields.Nested(header))
}

route_schedule_fields = {
    "table": PbField(table_field),
    "display_informations": PbField(display_informations_route,
                                    attribute='pt_display_informations'),
    "links": UrisToLinks(),
    "geojson": MultiLineString(),
    "additional_informations": enum_type(attribute="response_status")
}

route_schedules = {
    "error": PbField(error, attribute='error'),
    "route_schedules": fields.List(fields.Nested(route_schedule_fields)),
    "pagination": fields.Nested(pagination),
    "disruptions": fields.List(NonNullNested(disruption_marshaller), attribute="impacts"),
    "feed_publishers": fields.List(fields.Nested(feed_publisher))
}


class RouteSchedules(Schedules):

    def __init__(self):
        self.collections = route_schedules
        super(RouteSchedules, self).__init__("route_schedules",
                                             output_type_serializer=api.RouteSchedulesSerializer)


stop_schedule = {
    "stop_point": PbField(stop_point),
    "route": PbField(route, attribute="route"),
    "additional_informations": enum_type(attribute="response_status"),
    "display_informations": PbField(display_informations_route,
                                    attribute='pt_display_informations'),
    "date_times": fields.List(fields.Nested(date_time)),
    "links": UrisToLinks()
}
stop_schedules = {
    "stop_schedules": fields.List(fields.Nested(stop_schedule)),
    "pagination": fields.Nested(pagination),
    "error": PbField(error, attribute='error'),
    "disruptions": fields.List(NonNullNested(disruption_marshaller), attribute="impacts"),
    "feed_publishers": fields.List(fields.Nested(feed_publisher))
}


class StopSchedules(Schedules):

    def __init__(self):
        self.collections = stop_schedules
        super(StopSchedules, self).__init__("departure_boards",
                                            output_type_serializer=api.StopSchedulesSerializer)


passage = {
    "route": PbField(route),
    "stop_point": PbField(stop_point),
    "stop_date_time": PbField(stop_date_time),
    "display_informations": PbField(display_informations_vj,
                                    attribute='pt_display_informations'),
    "links": UrisToLinks()
}

departures = {
    "departures": fields.List(fields.Nested(passage),
                              attribute="next_departures"),
    "pagination": fields.Nested(pagination),
    "error": PbField(error, attribute='error'),
    "disruptions": fields.List(NonNullNested(disruption_marshaller), attribute="impacts"),
    "feed_publishers": fields.List(fields.Nested(feed_publisher))
}

arrivals = {
    "arrivals": fields.List(fields.Nested(passage), attribute="next_arrivals"),
    "pagination": fields.Nested(pagination),
    "error": PbField(error, attribute='error'),
    "disruptions": fields.List(NonNullNested(disruption_marshaller), attribute="impacts"),
    "feed_publishers": fields.List(fields.Nested(feed_publisher))
}

class add_passages_links:
    """
    delete disruption links and put the disruptions directly in the owner objets

    TEMPORARY: delete this as soon as the front end has the new disruptions integrated
    """
    def __call__(self, f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            response, status, other = f(*args, **kwargs)
            api = "departures" if "departures" in response else "arrivals" if "arrivals" in response else None
            if not api:
                return response, status, other
            passages = response[api]

            max_dt = "19000101T000000"
            min_dt = "29991231T235959"
            time_field = "arrival_date_time" if api == "arrivals" else "departure_date_time"
            for passage_ in passages:
                dt = passage_["stop_date_time"][time_field]
                if min_dt > dt:
                    min_dt = dt
                if max_dt < dt:
                    max_dt = dt
            if "links" not in response:
                response["links"] = []
            kwargs_links = dict(deepcopy(request.args))
            if "region" in kwargs:
                kwargs_links["region"] = kwargs["region"]
            if "uri" in kwargs:
                kwargs_links["uri"] = kwargs["uri"]
            if 'from_datetime' in kwargs_links:
                kwargs_links.pop('from_datetime')
            delta = timedelta(seconds=1)
            dt = datetime.strptime(min_dt, "%Y%m%dT%H%M%S")
            if g.stat_interpreted_parameters.get('data_freshness') != 'realtime':
                if "templated" in kwargs_links:
                    del kwargs_links["kwargs"]
                kwargs_links['until_datetime'] = (dt - delta).strftime("%Y%m%dT%H%M%S")
                response["links"].append(create_external_link("v1."+api, rel="prev", _type=api, **kwargs_links))
                kwargs_links.pop('until_datetime')
                kwargs_links['from_datetime'] = (datetime.strptime(max_dt, "%Y%m%dT%H%M%S") + delta).strftime("%Y%m%dT%H%M%S")
                response["links"].append(create_external_link("v1."+api, rel="next", _type=api, **kwargs_links))
            return response, status, other
        return wrapper


class NextDepartures(Schedules):

    def __init__(self):
        self.collections = departures
        super(NextDepartures, self).__init__("next_departures",
                                             output_type_serializer=api.DeparturesSerializer)
        self.get_decorators.append(add_passages_links())


class NextArrivals(Schedules):

    def __init__(self):
        self.collections = arrivals
        super(NextArrivals, self).__init__("next_arrivals",
                                           output_type_serializer=api.ArrivalsSerializer)
        self.get_decorators.append(add_passages_links())
