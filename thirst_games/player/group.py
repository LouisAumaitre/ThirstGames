from random import random
from typing import List, Optional, Union

from copy import copy

from thirst_games.items import Weapon, Item, Bag, HANDS
from thirst_games.map import Positionable, Area
from thirst_games.narrator import format_list, Narrator
from thirst_games.player.player import Player
from thirst_games.player.playing_entity import PlayingEntity


class Group(PlayingEntity):
    def __init__(self, players: List[Player]):
        if not len(players):
            raise ValueError
        self.players = players
        self.acting_players = copy(players)
        self.move_to(players[0].current_area)
        self.map = players[0].map

    def __str__(self):
        return f'G({format_list([p.name for p in self.players])})'

    def think(self):
        strats = {}
        for a in self.players:
            for s, v in a.judge_strats().items():
                strats[s] = strats.get(s, 0) + v
        self.strategy = [s for s, v in strats.items() if v == max(strats.values())][0]
        print(f'{str(self)}:{self.strategy.name}')
        for a in self.players:
            a.strategy = self.strategy

    def act(self):
        Narrator().cut()
        self.acting_players = []
        for p in self.players:
            if p.new_strat() == self.strategy:
                self.acting_players.append(p)
            else:
                print(f'{p.name}:{p.strategy}, group:{self.strategy}')
                p.act()
        if len(self.acting_players):
            self.strategy.apply(self)
        Narrator().cut()

    def reset_turn(self):
        for p in self.players:
            self.strategy = None
            self.acted = False

    @property
    def is_alive(self):
        return sum(p.is_alive for p in self.players) > 0

    def courage(self):
        return max(p.courage for p in self.players)

    def dangerosity(self):
        return sum(p.courage for p in self.players)

    def flee(self, panic=False, drop_verb='drops', stock=False):
        raise NotImplementedError

    def pursue(self):
        raise NotImplementedError

    def enemies(self, area: Area) -> List[Positionable]:
        return [p for p in area.players if p != self]  # TODO: consider

    def set_up_ambush(self):
        raise NotImplementedError

    def estimate_of_power(self, area) -> float:
        raise NotImplementedError

    def estimate_of_danger(self, area) -> float:
        raise NotImplementedError

    def can_see(self, other):
        raise NotImplementedError

    def pillage(self, stuff):
        raise NotImplementedError

    def attack_at_random(self):
        raise NotImplementedError

    def fight(self, other_player):
        raise NotImplementedError

    def loot_weapon(self, weapon: Optional[Union[Weapon, List[Weapon]]]=None):
        weapons: List[Weapon] = []
        if isinstance(weapon, Weapon):
            weapons.append(weapon)
        if isinstance(weapon, list):
            weapons = weapon
        if weapon is None:
            for _ in self.acting_players:
                weapons.append(self.map.pick_weapon(self))
        weapons = [w for w in weapons if w is not None]

        weapons.sort(key=lambda x: -x.damage_mult)
        self.acting_players.sort(key=lambda x: -x.weapon.damage_mult)

        picked = False
        for player in self.acting_players:
            for weapon in weapons:
                if weapon.damage_mult > player.weapon.damage_mult:
                    if weapon.name == player.weapon.name:
                        player.weapon.long_name.replace('\'s', '\'s old')
                        Narrator().add([player.first_name, 'picks up', f'a better {weapon.name}', self.current_area.at])
                    else:
                        Narrator().add([player.first_name, 'picks up', weapon.long_name, self.current_area.at])
                    if player.weapon != HANDS:
                        weapons.append(player.weapon)
                    player.get_weapon(weapon)
                    weapons.remove(weapon)
                    picked = True
                    break
        if not picked:
            Narrator().add([
                format_list([p.first_name for p in self.acting_players]), 'try to find weapons', self.current_area.at,
                'but can\'t find anything good'])

    def loot_bag(self):
        items: List[Item] = []
        for _ in self.acting_players:
            b = self.map.pick_bag(self)
            if b is None:
                b = self.map.pick_item(self)
            if b is not None:
                items.append(b)

        if not len(items):
            Narrator().add([
                format_list([p.first_name for p in self.acting_players]), 'try to find loot', self.current_area.at,
                'but can\'t find anything good'])
            return

        items.sort(key=lambda x: (isinstance(x, Bag)) * 10 + random())
        self.acting_players.sort(key=lambda x: (x.bag is not None) * 10 + random())

        for player in self.acting_players:
            item = items.pop(0)
            Narrator().add([player.first_name, 'picks up', item.long_name, self.current_area.at])
            player.get_item(item)
