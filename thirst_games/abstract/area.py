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


class Area:
    def __init__(self, name: str, ):
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
        if self.name == 'river':
            return True
        return False

    @property
    def is_start(self) -> bool:
        return self.name == START_AREA

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'{self.name}: {[p.name for p in self.players]}'
