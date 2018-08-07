from random import random
from typing import List, Optional, Union

from copy import copy

from thirst_games.items import Weapon, Item, Bag, HANDS
from thirst_games.map import Positionable, Area
from thirst_games.narrator import format_list, Narrator
from thirst_games.player.player import Player
from thirst_games.player.playing_entity import PlayingEntity


def player_names(players: List[Player]) -> str:
    return format_list([p.first_name for p in players])


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
            player_strat = p.new_strat()
            if player_strat == self.strategy:
                self.acting_players.append(p)
            else:
                if player_strat is not None:
                    print(f'{p.name}:{player_strat.name}, group:{self.strategy.name}')
                p.apply_strat(player_strat)
        if len(self.acting_players):
            self.strategy.apply(self)
        Narrator().cut()
        self.acted = True

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
        # TODO: group fight
        for player in self.acting_players:
            player.attack_at_random()

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

        empty_handed: List[Player] = []
        for player in self.acting_players:
            picked = False
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
                empty_handed.append(player)
        if len(empty_handed):
            verb = 'try' if len(empty_handed) > 1 else 'tries'
            Narrator().add([
                player_names(empty_handed), verb, 'to find weapons', self.current_area.at,
                'but can\'t find anything good'])

    def loot_bag(self):
        items: List[Item] = []
        for _ in self.acting_players:
            b = self.map.pick_bag(self)
            if b is None:
                b = self.map.pick_item(self)
            if b is not None:
                items.append(b)

        items.sort(key=lambda x: (isinstance(x, Bag)) * 10 + random())
        self.acting_players.sort(key=lambda x: (x.bag is not None) * 10 + random())

        empty_handed: List[Player] = []
        for player in self.acting_players:
            if len(items):
                item = items.pop(0)
                Narrator().add([player.first_name, 'picks up', item.long_name, self.current_area.at])
                player.get_item(item)
            else:
                empty_handed.append(player)

        if len(empty_handed):
            verb = 'try' if len(empty_handed) > 1 else 'tries'
            Narrator().add([
                player_names(empty_handed), verb, 'to find loot', self.current_area.at,
                'but can\'t find anything good'])

    def loot(self, take_a_break=True):
        items: List[Item] = []
        for _ in self.acting_players:
            b = self.map.pick_item(self)
            if b is not None:
                items.append(b)

        items.sort(key=lambda x: random())
        self.acting_players.sort(key=lambda x: random())

        empty_handed: List[Player] = []
        for player in self.acting_players:
            if len(items):
                item = items.pop(0)
                Narrator().add([player.first_name, 'picks up', item.long_name, self.current_area.at])
                player.get_item(item)
            else:
                empty_handed.append(player)

        if len(empty_handed):
            verb = 'try' if len(empty_handed) > 1 else 'tries'
            Narrator().add([
                player_names(empty_handed), verb, 'to find loot', self.current_area.at,
                'but can\'t find anything good'])

    def hide(self, panic=False, stock=False):
        if panic:
            Narrator().add([player_names(self.acting_players), 'hides', self.current_area.at], stock=stock)
            return
        for player in self.acting_players:
            player.hide(stock=stock)
        # if self.sleep < 0.1 \
        #         or (Context().time == NIGHT and self.map.players_count == 1 and len(self.wounds) == 0) \
        #         or (self.map.players_count == 1 and self.sleep < 0.2 and len(self.wounds) == 0) \
        #         or (Context().time == NIGHT and self.sleep < 0.3 and len(self.wounds) == 0):
        #     self.go_to_sleep(stock=stock)
        #     return
        # return self.rest(stock=stock)

    def craft(self):
        for player in self.acting_players:
            player.craft()

    def reveal(self):
        for p in self.acting_players:
            p.reveal()

    def go_to(self, area: Union[str, Area, Positionable]) -> Optional[Area]:
        area = self.map.get_area(area)
        if area != self.current_area:
            for p in self.acting_players:
                p.go_to(area)
            return self.map.move_player(self, area)
        return None

    def go_get_drop(self):
        out = self.go_to(self.destination)
        if out is not None:
            Narrator().add([player_names(self.acting_players), f'goes {out.to} to get loot'])
        else:
            Narrator().cut()
        if self.check_for_ambush_and_traps():
            return
        seen_neighbors = [p for p in self.map.potential_players(self) if self.can_see(p) and p != self]
        free_neighbors = [p for p in seen_neighbors if p.current_area == self.current_area and not p.busy]
        potential_danger = sum([p.dangerosity() for p in seen_neighbors])
        actual_danger = sum([p.dangerosity() for p in free_neighbors])

        if potential_danger > self.dangerosity() and potential_danger > self.courage():
            Narrator().add([player_names(self.acting_players), 'see', format_list([p.first_name for p in seen_neighbors])])
            self.flee()
        elif actual_danger > self.dangerosity() and actual_danger > self.courage():
            Narrator().add([player_names(self.acting_players), 'see', format_list([p.first_name for p in free_neighbors])])
            self.flee()
        elif actual_danger > 0:  # enemy present -> fight them
            Narrator().cut()
            self.attack_at_random()
        elif potential_danger > 0 and actual_danger == 0:  # enemy busy but incoming
            if self.dangerosity() > potential_danger:  # attack before the other(s) arrive
                Narrator().cut()
                self.attack_at_random()
            else:  # loot and go/get your load and hit the road
                Narrator().add([player_names(self.acting_players), 'avoid', format_list([p.first_name for p in seen_neighbors])])
                self.loot(take_a_break=False)
                self.flee()
        else:  # servez-vous
            self.loot()
        if len(Narrator().current_sentence) == 0:
            Narrator().add([
                str(self), f'potential_danger={potential_danger}', f'actual_danger={actual_danger}',
                f'dangerosity={self.dangerosity()}', f'courage={self.courage()}',
            ])