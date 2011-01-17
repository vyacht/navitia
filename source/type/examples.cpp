#include "indexes.h"
#include <iostream>
#include <boost/foreach.hpp>
#include <boost/assign/std/vector.hpp>
#include <boost/assign.hpp>
#include <vector>

struct Stop {
    int id;
    std::string name;
    std::string city;
    Stop(int id, const std::string & name, const std::string & city) : id(id), name(name), city(city) {}
};

struct Line {
    std::string name;
    float duration;
    Line(const std::string & name, float duration) : name(name), duration(duration) {}
};

struct City {
    std::string name;
    std::string country;
    City(const std::string & name, const std::string & country) : name(name), country(country) {}
};

struct LineStops {
    int stop_id;
    std::string line_name;
    int order;
    LineStops(int stop_id, const std::string & line_name, int order): stop_id(stop_id), line_name(line_name), order(order) {}
};

using namespace boost::assign;

int main(int, char**) {
    std::vector<Stop> stops;
    std::vector<Line> lines;
    std::vector<City> cities;
    std::vector<LineStops> line_stops;

    stops += Stop(0, "Gare de l'Est", "Paris"),
             Stop(1, "Gare d'Austeriltz", "Paris"),
             Stop(2, "Westbahnhof", "Wien"),
             Stop(3, "Hauptbahnof", "Stuttgart"),
             Stop(4, "Centre du monde", "Perpinyà"),
             Stop(5, "Sants", "Barcelona");

    lines += Line("Orient Express", 15.5),
             Line("Joan Miró", 12.1),
             Line("Metro 5", 0.1);


    cities += City("Paris", "France"),
              City("Wien", "Österreich"),
              City("Stuttgart", "Deutschland"),
              City("Barcelona", "España"),
              City("Pepinyà", "France");

    line_stops += LineStops(0, "Orient Express", 0),
                  LineStops(3, "Orient Express", 1),
                  LineStops(2, "Orient Express", 2),
                  LineStops(1, "Joan Miró", 1),
                  LineStops(5, "Joan Miró", 66),
                  LineStops(4, "Joan Miró", 42),
                  LineStops(0, "Metro 5", 1),
                  LineStops(1, "Metro 5", 2);


    std::cout << "=== Cities ordered by name ===" << std::endl;
    BOOST_FOREACH(auto city, order(cities, &City::name)){
        std::cout << "  * " << city.name << " (" << city.country << ")" << std::endl;
    }
    std::cout << std::endl << std::endl;

    std::cout << "=== Stations of Paris ===" << std::endl;
    BOOST_FOREACH(auto stop, filter(stops, &Stop::city, std::string("Paris"))){
        std::cout << "  * " << stop.name << std::endl;
    }
    std::cout << std::endl << std::endl;

    std::cout << "=== Stops of line Orient Express ===" << std::endl;
    auto join = make_join(stops,
                          filter(line_stops, &LineStops::line_name, std::string("Orient Express")),
                          attribute_equals(&Stop::id, &LineStops::stop_id));
    BOOST_FOREACH(auto stop, join){
        std::cout << "  * " << join_get<0>(stop).name << " " << join_get<1>(stop).order << std::endl;
    }

    std::cout << "=== Stops of line Orient Express (bis) ===" << std::endl;
    auto join2 = make_join(filter(line_stops, &LineStops::line_name, std::string("Orient Express")),
                           stops,
                           attribute_equals(&LineStops::stop_id, &Stop::id));
    BOOST_FOREACH(auto stop, join2){
        std::cout << "  * " << join_get<1>(stop).name << " " << join_get<0>(stop).order << std::endl;
    }

    std::cout << "=== Stops of line Orient Express in Paris ===" << std::endl;
    auto join3 = make_join(filter(line_stops, &LineStops::line_name, std::string("Orient Express")),
                           filter(stops, &Stop::city, std::string("Paris")),
                           attribute_equals(&LineStops::stop_id, &Stop::id));
    BOOST_FOREACH(auto stop, join3){
        std::cout << "  * " << join_get<1>(stop).name << " " << join_get<0>(stop).order << std::endl;
    }

    std::cout << "=== (Stops, Lines) couples ===" << std::endl;
    auto join4 = make_join(line_stops,
                           stops,
                           attribute_equals(&LineStops::stop_id, &Stop::id));
    BOOST_FOREACH(auto stop, join4){
        std::cout << "  * " << join_get<1>(stop).name << ", " << join_get<0>(stop).line_name << std::endl;
    }
/*
    std::cout << "=== Lines stoping in France ===" << std::endl;
    auto join5 = make_join(
                           make_join(filter(cities, &City::country, "France"), stops),
                           line_stops,
                           attribute_equals(&LineStops::stop_id, &Stop::id));
    BOOST_FOREACH(auto stop, join5){
        std::cout << "  * " << join_get<LineStop>(stop).line_name << ", " << join_get<1>(stop).name << std::endl;
    }*/

    return 0;
}
