from random import random

weapon_kill_word = {
    'axe': ['decapitates'],
    'sword': ['decapitates', 'stabs'],
    'knife': ['stabs'],
    'trident': ['stabs'],
    'spear': ['stabs'],
    'bare hands': ['strangle'],
    'club': [],
    'default': [],
}
for key, value in weapon_kill_word.items():
    value.append('kills')

weapon_wound_proba = {
    'axe': [('arm', 0.4), ('leg', 0.1)],
    'sword': [('arm', 0.3), ('leg', 0.2), ('belly', 0.2)],
    'knife': [('arm', 0.2), ('leg', 0.05), ('belly', 0.3)],
    'trident': [('arm', 0.4), ('leg', 0.2), ('belly', 0.2)],
    'spear': [('arm', 0.3), ('leg', 0.15), ('belly', 0.15)],
    'bare hands': [('arm', 0.2), ('leg', 0.2)],
    'club': [('head', 0.4), ('arm', 0.1), ('leg', 0.05)],
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
    'axe': 0.5,
    'sword': 0.5,
    'knife': 0.3,
    'trident': 0.4,
    'spear': 0.4,
    'bare hands': 0,
    'club': 0,
    'default': 0,
}


def get_weapon_blood(weapon_name):
    weapon_proba = weapon_bleed_proba.get(weapon_name, weapon_bleed_proba['default'])
    r = random()
    return r < weapon_proba
