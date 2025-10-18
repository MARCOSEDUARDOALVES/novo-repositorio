from kerykeion import AstrologicalSubject
import json

def point_to_dict(point):
    return {
        "name": point.name,
        "quality": point.quality,
        "element": point.element,
        "sign": point.sign,
        "sign_num": point.sign_num,
        "position": point.position,
        "abs_pos": point.abs_pos,
        "emoji": point.emoji,
        "point_type": point.point_type,
        "house": point.house,
        "retrograde": point.retrograde
    }

def house_to_dict(house):
    # Atributos disponíveis para objetos de casa (KerykeionPointModel) são os mesmos de planetas, mas com valores específicos para casas.
    # 'cusp', 'ruler' e 'ruler_house' não são atributos diretos do objeto house.
    return {
        "name": house.name,
        "quality": house.quality,
        "element": house.element,
        "sign": house.sign,
        "sign_num": house.sign_num,
        "position": house.position, # A posição da cúspide da casa
        "abs_pos": house.abs_pos,
        "emoji": house.emoji,
        "point_type": house.point_type,
        "house": house.house,
        "retrograde": house.retrograde
    }

john = AstrologicalSubject("John Lennon", 1940, 10, 9, 18, 30, "Liverpool", "GB", lng=-2.983333, lat=53.400002, tz_str="Europe/London")

chart_data = {
    "name": john.name,
    "year": john.year,
    "month": john.month,
    "day": john.day,
    "hour": john.hour,
    "minutes": john.minute,
    "city": john.city,
    "nation": john.nation,
    "longitude": john.lng,
    "latitude": john.lat,
    "tz_str": john.tz_str,
    "sun": point_to_dict(john.sun),
    "moon": point_to_dict(john.moon),
    "mercury": point_to_dict(john.mercury),
    "venus": point_to_dict(john.venus),
    "mars": point_to_dict(john.mars),
    "jupiter": point_to_dict(john.jupiter),
    "saturn": point_to_dict(john.saturn),
    "uranus": point_to_dict(john.uranus),
    "neptune": point_to_dict(john.neptune),
    "pluto": point_to_dict(john.pluto),
    "chiron": point_to_dict(john.chiron),
    "lilith": point_to_dict(john.mean_lilith),
    "north_node": point_to_dict(john.true_node),
    "south_node": point_to_dict(john.true_south_node),
    "ascendant": point_to_dict(john.ascendant),
    "mc": point_to_dict(john.medium_coeli),
    "houses": [
        house_to_dict(john.first_house),
        house_to_dict(john.second_house),
        house_to_dict(john.third_house),
        house_to_dict(john.fourth_house),
        house_to_dict(john.fifth_house),
        house_to_dict(john.sixth_house),
        house_to_dict(john.seventh_house),
        house_to_dict(john.eighth_house),
        house_to_dict(john.ninth_house),
        house_to_dict(john.tenth_house),
        house_to_dict(john.eleventh_house),
        house_to_dict(john.twelfth_house)
    ]
}

with open("john_lennon_chart.json", "w") as f:
    f.write(json.dumps(chart_data, indent=4))

