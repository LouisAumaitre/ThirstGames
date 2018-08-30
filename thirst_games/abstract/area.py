from typing import Any, List

from thirst_games.constants import START_AREA

_nature = {
    START_AREA: {
        'food': []
    }, 'ruins': {
        'food': ['roots']
    }, 'forest': {
        'food': ['roots', 'fruits', 'mushrooms', 'berries']
    }, 'plain': {
        'food': ['roots', 'berries']
    }, 'rocks': {
        'food': []
    }, 'jungle': {
        'food': ['roots', 'fruits']
    }, 'river': {
        'food': ['roots', 'algae']
    }, 'hill': {
        'food': ['roots']
    }
}

_ids = {}


class Area:
    def __init__(self, name: str):
        if name in _ids:
            _ids[name] += 1
            self.id = _ids[name]
        else:
            _ids[name] = 0
            self.id = 0
        self.name = name
        self.at = f'at the {name}'
        self.to = f'to the {name}'
        self.foods: List[str] = _nature[name]['food']
        self.players: List[Any] = []
        self.loot: List[Any] = []
        self.traps: List[Any] = []
        self.ambushers: List[Any] = []

    @property
    def has_water(self) -> bool:
        return self.name in ['river', 'lake']

    @property
    def is_start(self) -> bool:
        return self.name == START_AREA

    @property
    def full_name(self):
        return f'{self.name}[{self.id}]'

    def __str__(self):
        # return self.name
        return f'{self.name}[{self.id}]'

    def __repr__(self):
        return f'{self.name}[{self.id}]: {[p.name for p in self.players]}'
