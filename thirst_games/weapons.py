from random import random

from thirst_games.constants import AXE, KNIFE, SWORD, TRIDENT, SPEAR, CLUB, HATCHET, MACE, MACHETE

weapon_kill_word = {
    AXE: ['decapitates'],
    SWORD: ['decapitates', 'stabs'],
    KNIFE: ['stabs'],
    TRIDENT: ['stabs'],
    SPEAR: ['stabs'],
    'bare hands': ['strangle'],
    CLUB: [],
    'default': [],
}
for key, value in weapon_kill_word.items():
    value.append('kills')

weapon_wound_proba = {
    AXE: [('arm', 0.4), ('leg', 0.1)],
    SWORD: [('arm', 0.3), ('leg', 0.2), ('belly', 0.2)],
    MACHETE: [('arm', 0.25), ('leg', 0.1), ('belly', 0.15)],
    KNIFE: [('arm', 0.2), ('leg', 0.05), ('belly', 0.3)],
    HATCHET: [('arm', 0.2), ('leg', 0.05), ('belly', 0.3)],
    TRIDENT: [('arm', 0.4), ('leg', 0.2), ('belly', 0.2)],
    SPEAR: [('arm', 0.3), ('leg', 0.15), ('belly', 0.15)],
    'bare hands': [('arm', 0.2), ('leg', 0.2)],
    CLUB: [('head', 0.4), ('arm', 0.1), ('leg', 0.05)],
    MACE: [('head', 0.5), ('arm', 0.2), ('leg', 0.05)],
    'fire': [('burn', 0.9)],
    'default': [('arm', 0.2), ('leg', 0.2)],
}


def get_weapon_wound(weapon_name):
    weapon_proba = weapon_wound_proba.get(weapon_name, weapon_wound_proba['default'])
    r = random()
    for element, proba in weapon_proba:
        if r < proba:
            return element
        r -= proba
    return None


weapon_bleed_proba = {
    AXE: 0.5,
    SWORD: 0.5,
    KNIFE: 0.3,
    HATCHET: 0.3,
    TRIDENT: 0.4,
    SPEAR: 0.4,
    'bare hands': 0,
    CLUB: 0,
    'default': 0,
}


def get_weapon_blood(weapon_name):
    weapon_proba = weapon_bleed_proba.get(weapon_name, weapon_bleed_proba['default'])
    r = random()
    return r < weapon_proba
