from typing import List, Union, Optional

from random import random, choice, randint

from thirst_games.abstract.entity import Entity, AbstractTrap, CarryingEntity
from thirst_games.abstract.items import Weapon, Item, Bag, Bottle, PoisonVial
from thirst_games.abstract.area import Area, _nature
from thirst_games.abstract.playing_entity import PlayingEntity
from thirst_games.constants import KNIFE, HATCHET, TRIDENT, AXE, SWORD, MACE, START_AREA, MACHETE
from thirst_games.poison import Poison, Food
from thirst_games.singleton import Singleton

food_values = {
    'roots': 0.3,
    'algae': 0.5,
    'mushrooms': 0.7,
    'berries': 0.6,
    'fruits': 0.8,
    'ration': 1,
}


def random_bag() -> Bag:
    elements = []
    for i in range(1 + randint(0, 2) + randint(0, 2)):
        elements.append(Food(choice(['ration', 'food can', 'energy bar']), 0.5 + random() / 2))
    if random() > 0.3:
        elements.append(Item('rope'))
    if random() > 0.2:
        for i in range(randint(1, 4)):
            elements.append(Item('bandages'))
    if random() > 0.2:
        for i in range(randint(1, 4)):
            elements.append(Item('iodine'))
    if random() > 0.7:
        elements.append(Item('net'))
    if random() > 0.7:
        elements.append(Item('wire'))
    if random() > 0.6:
        elements.append(Item('antidote'))
    if random() > 0.9:
        elements.append(PoisonVial(Poison('poison', randint(3, 6), random() * 0.2 + 0.1)))
    if random() > 0.2:
        elements.append(Bottle(float(random() > 0.5)))
    if random() > 0.8:
        for i in range(randint(1, 3)):
            elements.append(Item('explosive'))
    if random() > 1/3:
        elements.append(Weapon(HATCHET, 1 + random()))
    elif random() > 0.5:
        elements.append(Weapon(KNIFE, 1 + random()))
    return Bag(elements)


def random_weapon() -> Weapon:
    potential_weapons = {
        (SWORD, 2.5): 1,
        (AXE, 2.5): 1,
        (MACE, 2): 0.5,
        (TRIDENT, 2.5): 0.1,
        (KNIFE, 1): 3,
        (MACHETE, 1.5): 2,
    }
    total = sum(potential_weapons.values())
    potential_weapons = {key: value / total for key, value in potential_weapons.items()}
    pick = random()
    for key, value in potential_weapons.items():
        if pick < value:
            name, power = key
            return Weapon(name, power + random())
        pick -= value
    raise ValueError


class Map(metaclass=Singleton):

    def __init__(self, player_amount=24) -> None:
        print(f'INIT ARENA FOR {player_amount} PLAYERS')
        possible_parts_names = list(_nature.keys())
        possible_parts_names.remove(START_AREA)
        possible_parts_names.sort(key=lambda x: random())
        size = player_amount // 4 + 1
        possible_parts_names = possible_parts_names[:size-1]
        self.areas: List[Area] = []
        for area_name in possible_parts_names:
            for i in range(randint(1, 4)):
                self.areas.append(Area(area_name))
        start_area = Area(START_AREA)
        self.areas.append(start_area)

        for i in range(player_amount // 2):
            start_area.loot.append(random_weapon())
        for i in range(5):
            start_area.loot.append(random_bag())

        self.test = ''

    @property
    def area_names(self) -> List[str]:
        return [area.name for area in self.areas]

    def get_area(self, area: Union[str, Area, Entity]) -> Area:
        if isinstance(area, Entity):
            return area.current_area
        if isinstance(area, str):
            try:
                return [a for a in self.areas if a.name == area][0]
            except IndexError as e:
                raise IndexError(f'no {area} in {self.areas}') from e
        if isinstance(area, Area):
            return area
        raise ValueError(f'{area} is neither a string or a positionable')

    def loot(self, area: Union[str, Area, Entity]) -> List[Item]:
        return self.get_area(area).loot

    def has_loot(self, area: Union[str, Area, Entity]) -> bool:
        return len(self.loot(area)) > 0

    def forage_potential(self, area: Union[str, Area, Entity]) -> float:
        foods = self.get_area(area).foods
        if len(foods):
            return max([food_values[name] for name in foods])
        return 0

    def get_forage(self, area: Union[str, Area, Entity]) -> Optional[Food]:
        foods = self.get_area(area).foods
        if not len(foods):
            return None
        food_name = choice(foods)
        return Food(food_name, random() * food_values[food_name])

    def weapons(self, area: Union[str, Area, Entity]) -> List[Weapon]:
        return [e for e in self.loot(area) if isinstance(e, Weapon)]

    def has_weapons(self, area: Union[str, Area, Entity]) -> bool:
        return len(self.weapons(area)) > 0

    def pick_weapon(self, area: Union[str, Area, Entity]) -> Optional[Weapon]:
        if not self.has_weapons(area):
            return None
        w = choice(self.weapons(area))
        self.remove_loot(w, area)
        return w

    def bags(self, area: Union[str, Area, Entity]) -> List[Bag]:
        return [e for e in self.loot(area) if isinstance(e, Bag)]

    def has_bags(self, area: Union[str, Area, Entity]) -> bool:
        return len(self.bags(area)) > 0

    def pick_bag(self, area: Union[str, Area, Entity]) -> Optional[Bag]:
        if not self.has_bags(area):
            return None
        b = choice(self.bags(area))
        self.remove_loot(b, area)
        return b

    def pick_item(self, area: Union[str, Area, Entity]):
        if not self.has_loot(area):
            return None
        i = choice(self.loot(area))
        self.remove_loot(i, area)
        return i

    def pick_best_item(self, player: CarryingEntity):
        if not self.has_loot(player):
            return None
        best_value = max([player.estimate(i) for i in self.loot(player)])
        picks = [i for i in self.loot(player) if player.estimate(i) == best_value]
        i = choice(picks)
        self.remove_loot(i, player)
        return i

    def remove_loot(self, item: Item, area: Union[str, Area, Entity]):
        try:
            self.get_area(area).loot.remove(item)
        except ValueError as e:
            print(f'WARNING: tried to remove {item.long_name} from loot at {area} but couldn\'t')

    def add_loot(self, item: Item, area: Union[str, Area, Entity]):
        self.get_area(area).loot.append(item)

    def add_player(self, player: Entity, destination: Union[str, Area, Entity]=START_AREA):
        area = self.get_area(destination)
        player.move_to(area)
        area.players.append(player)

    def remove_player(self, player: Entity):
        try:
            player.current_area.players.remove(player)
        except ValueError as e:
            for area in self.areas:
                print(f'{area.name}: {[p.name for p in area.players]}')
            raise e

    def move_player(self, player, destination: Union[str, Area, Entity]) -> Optional[Area]:
        new_area = self.get_area(destination)
        # Narrator().new([player.current_area.name, '->', player.name, '->', new_area.name])
        if player.current_area == new_area:
            return None
        self.remove_player(player)
        self.add_player(player, destination)
        return new_area

    def add_trap(self, trap: Entity, area: Union[str, Area, Entity]=START_AREA):
        area = self.get_area(area)
        trap.move_to(area)
        trap.map = self
        area.traps.append(trap)

    def remove_trap(self, trap: Entity):
        trap.current_area.traps.remove(trap)

    def players_count(self, area: Union[str, Area, Entity]) -> int:
        v = len(self.players(area))
        if not v and isinstance(area, Entity):
            print(f'Warning: {area.name} not in {area.current_area}? {area.current_area.players}')
        return v

    def players(self, area: Union[str, Area, Entity]) -> List[PlayingEntity]:
        return self.get_area(area).players

    def potential_players(self, area: Union[str, Area, Entity]) -> List[PlayingEntity]:
        area = self.get_area(area)
        return [p for a in self.areas for p in a.players if p.current_area == area or p.destination == area]

    def traps(self, area: Union[str, Area, Entity]) -> List[AbstractTrap]:
        return self.get_area(area).traps

    def has_water(self, area: Union[str, Area, Entity]) -> bool:
        return self.get_area(area).has_water

    def ambushers(self, area: Union[str, Area, Entity]):
        return self.get_area(area).ambushers

    def add_ambusher(self, ambusher: PlayingEntity, area: Union[str, Area, Entity]):
        print(f'add ambucher: {ambusher.name}')
        area_ambushers = self.get_area(area).ambushers
        if ambusher not in area_ambushers:
            for p in ambusher.players:
                for prev_ambush in area_ambushers:
                    if p in prev_ambush.players:
                        area_ambushers.remove(prev_ambush)
                        break
            area_ambushers.append(ambusher)

    def remove_ambusher(self, ambusher):
        for area in self.areas:
            if ambusher in area.ambushers:
                area.ambushers.remove(ambusher)
