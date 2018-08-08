from typing import List, Optional, Union, Dict

from copy import copy
from random import random, choice

from thirst_games.abstract.area import Area
from thirst_games.abstract.entity import Entity
from thirst_games.abstract.items import Weapon, Item, Bag, HANDS, Food
from thirst_games.abstract.playing_entity import PlayingEntity
from thirst_games.context import Context
from thirst_games.map import Map
from thirst_games.narrator import format_list, Narrator
from thirst_games.player.fight import do_a_fight
from thirst_games.player.player import Player, loot_start_strat, start_strategies


def player_names(players: List[Player]) -> str:
    return format_list([p.name for p in players])


class Group(PlayingEntity):
    def __init__(self, players: List[Player]) -> None:
        PlayingEntity.__init__(self, 'group', 'it')
        if not len(players):
            raise ValueError
        self._players = players
        self._acting_players = copy(players)
        self.move_to(players[0].current_area)

    @property
    def players(self):
        return [p for p in self._players if p.is_alive]

    @property
    def name(self) -> str:
        return f'{self.acting_players[0].name}\'s group'

    @property
    def acting_players(self) -> List[Player]:
        return [p for p in self._acting_players if p.is_alive]

    @property
    def current_area(self):
        return self.acting_players[0].current_area

    def __str__(self):
        return f'G({format_list([p.name for p in self.players])})'

    def think(self):
        strats = {}
        for a in self.players:
            for s, v in a.judge_strats().items():
                strats[s] = strats.get(s, 0) + v
        self.strategy = [s for s, v in strats.items() if v == max(strats.values())][0]
        # print(f'{str(self)}:{self.strategy.name}')
        for a in self.players:
            a.strategy = self.strategy

        if self.strategy == loot_start_strat:
            for x in self.players:
                w = x.estimate(Map().weapons(x))
                b = x.weapon.damage_mult * Map().has_bags(x) * (x.bag is None)
                if w == b == 0:
                    print(x.name)
                    print(f'w={round(w, 2)} b={round(b, 2)}')
                    for s in start_strategies():
                        print(f'{s.name}: {s.pref(x)}')

    def act(self):
        Narrator().cut()
        self._acting_players = []
        for p in self.players:
            player_strat = p.new_strat()
            if player_strat == self.strategy:
                self._acting_players.append(p)
            else:
                if player_strat is not None:
                    print(f'{p.name}:{player_strat.name}, group:{self.strategy.name}')
                p.apply_strat(player_strat)
        if len(self.acting_players) > 1:
            self.strategy.apply(self)
        elif len(self.acting_players) == 1:
            self.strategy.apply(self.acting_players[0])
        Narrator().cut()
        self.acted = True

    def reset_turn(self):
        for p in self.players:
            p.strategy = None
            p.acted = False
        self.strategy = None
        self.acted = False

    @property
    def is_alive(self):
        return sum(p.is_alive for p in self.players) > 0

    @property
    def courage(self) -> float:
        return max(p.courage for p in self.players)

    @property
    def dangerosity(self) -> float:
        return sum(p.courage for p in self.players)

    def flee(self, panic=False, drop_verb='drops', stock=False, filtered_areas=None):
        for player in self.acting_players:
            player.flee(panic=panic, drop_verb=drop_verb, stock=stock, filtered_areas=filtered_areas)

    def pursue(self):
        available_areas = [a for a in Map().areas if a not in Context().forbidden_areas]
        available_areas.sort(key=lambda x: sum(p._pursue_value(x) for p in self.acting_players))
        out = self.go_to(available_areas[-1])
        if out is None:
            self.hide()
            Narrator().replace('hides and rests', 'rests')
        else:
            targets = [p.name for p in Context().alive_players if p not in self.players]
            players = 'players' if len(targets) > 2 else format_list(targets)
            Narrator().add([self.name, 'searches for', players, out.at])
            self.check_for_ambush_and_traps()

    def enemies(self, area: Area) -> List[PlayingEntity]:
        return [p for p in Context().playing_entities_at(area) if p != self]  # TODO: consider

    def set_up_ambush(self):
        self.stealth += (random() / 2 + 0.5) * (1 - self.stealth)
        Map().add_ambusher(self, self)
        Narrator().add([self.name, 'sets up', 'an ambush', self.current_area.at])

    def estimate_of_power(self, area) -> float:
        raise NotImplementedError

    def estimate_of_danger(self, area) -> float:
        raise NotImplementedError

    def can_see(self, other):
        for player in self.acting_players:
            if isinstance(other, PlayingEntity):
                for target in other.players:
                    if player.can_see(target):
                        return True
            elif player.can_see(other):
                return True
        return False

    def pillage(self, stuff):
        raise NotImplementedError

    def attack_at_random(self):
        preys = [
            p for p in self.enemies(self.current_area)
            if self.can_see(p) and not set(self.players).intersection(set(p.players))
        ]
        preys.sort(key=lambda x: x.dangerosity)
        if len(preys):
            self.fight(preys[0])
        else:
            self.pursue()

    def fight(self, other_player: PlayingEntity):
        do_a_fight(self.acting_players, other_player.players)

    def loot_weapon(self, weapon: Optional[Union[Weapon, List[Weapon]]]=None):
        weapons: List[Weapon] = []
        if isinstance(weapon, Weapon):
            weapons.append(weapon)
        if isinstance(weapon, list):
            weapons = weapon
        if weapon is None:
            for _ in self.acting_players:
                weapons.append(Map().pick_weapon(self))
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
                        Narrator().add([player.name, 'picks up', f'a better {weapon.name}', self.current_area.at])
                    else:
                        Narrator().add([player.name, 'picks up', weapon.long_name, self.current_area.at])
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
            b = Map().pick_bag(self)
            if b is None:
                b = Map().pick_item(self)
            if b is not None:
                items.append(b)

        items.sort(key=lambda x: (isinstance(x, Bag)) * 10 + random())
        self.acting_players.sort(key=lambda x: (x.bag is not None) * 10 + random())

        empty_handed: List[Player] = []
        for player in self.acting_players:
            if len(items):
                item = items.pop(0)
                Narrator().add([player.name, 'picks up', item.long_name, self.current_area.at])
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
            b = Map().pick_item(self)
            if b is not None:
                items.append(b)

        items.sort(key=lambda x: random())
        self.acting_players.sort(key=lambda x: random())

        empty_handed: List[Player] = []
        for player in self.acting_players:
            if len(items):
                item = items.pop(0)
                Narrator().add([player.name, 'picks up', item.long_name, self.current_area.at])
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
        #         or (Context().time == NIGHT and Map().players_count == 1 and len(self.wounds) == 0) \
        #         or (Map().players_count == 1 and self.sleep < 0.2 and len(self.wounds) == 0) \
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

    def estimate(self, item) -> float:
        raise NotImplementedError

    def go_to(self, area: Union[str, Area, Entity]) -> Optional[Area]:
        area = Map().get_area(area)
        if area != self.current_area:
            for p in self.acting_players:
                p.go_to(area)
            return Map().move_player(self, area)
        return None

    def go_get_drop(self, area: Area):
        out = self.go_to(area)
        if out is not None:
            Narrator().add([player_names(self.acting_players), f'goes {out.to} to get loot'])
        else:
            Narrator().cut()
        if self.check_for_ambush_and_traps():
            return
        seen_neighbors = [p for p in Map().potential_players(self) if self.can_see(p) and p not in self.players]
        free_neighbors = [p for p in seen_neighbors if p.current_area == self.current_area and not p.busy]
        potential_danger = sum([p.dangerosity for p in seen_neighbors])
        actual_danger = sum([p.dangerosity for p in free_neighbors])

        if potential_danger > self.dangerosity and potential_danger > self.courage:
            Narrator().add([
                player_names(self.acting_players), 'see', format_list([p.name for p in seen_neighbors])])
            self.flee(filtered_areas=[area])
        elif actual_danger > self.dangerosity and actual_danger > self.courage:
            Narrator().add([
                player_names(self.acting_players), 'see', format_list([p.name for p in free_neighbors])])
            self.flee(filtered_areas=[area])
        elif actual_danger > 0:  # enemy present -> fight them
            Narrator().cut()
            self.attack_at_random()
        elif potential_danger > 0 and actual_danger == 0:  # enemy busy but incoming
            if self.dangerosity > potential_danger:  # attack before the other(s) arrive
                Narrator().cut()
                self.attack_at_random()
            else:  # loot and go/get your load and hit the road
                Narrator().add([
                    player_names(self.acting_players), 'avoid', format_list([p.name for p in seen_neighbors])])
                self.loot(take_a_break=False)
                self.flee(filtered_areas=[area])
        else:  # servez-vous
            self.loot()
        # if len(Narrator().current_sentence) == 0:
        #     Narrator().add([
        #         str(self), f'potential_danger={potential_danger}', f'actual_danger={actual_danger}',
        #         f'dangerosity={self.dangerosity}', f'courage={self.courage}',
        #     ])

    def check_for_ambush_and_traps(self):
        traps = Map().traps(self)
        for t in traps:
            if t.check(self):
                t.apply(self)
                return True
        ambushers = Map().ambushers(self)
        if not len(ambushers):
            return False
        ambusher = choice(ambushers)
        ambusher.trigger_ambush(self)
        return True

    def trigger_ambush(self, prey):
        Map().remove_ambusher(self, self)
        Narrator().new([prey.first_name, 'falls', 'into', f'{self.name}\'s ambush!'])
        self.fight(prey)

    def take_a_break(self):
        for player in self.acting_players:
            player.take_a_break()

    def forage(self):
        for player in self.acting_players:
            player.forage()

    def dine(self):
        self.take_a_break()
        food_owner: Dict[Food, Player] = {}
        for player in self.acting_players:
            for e in player.equipment:
                if isinstance(e, Food):
                    food_owner[e] = player
        if not len(food_owner):
            Narrator().add([self.name, 'does not have', 'anything to eat'])
        else:
            food = list(food_owner.keys())
            food.sort(key=lambda x: x.value)
            diner = {p: [] for p in self.acting_players}
            poison = {p: None for p in self.acting_players}
            eaters = copy(self.acting_players)
            eaters.sort(key=lambda x: -x.hunger)
            while len(eaters) and len(food):
                eaters_this_round = copy(eaters)
                for eater in eaters_this_round:
                    try:
                        meal = food.pop()
                    except IndexError:
                        break
                    food_owner[meal].remove_item(meal)
                    diner[eater].append(meal.name)
                    if eater.eat(meal, verbose=False) == 'poison':
                        poison[eater] = meal
                        eaters.remove(eater)
                    elif not eater.hunger:
                        eaters.remove(eater)

            for player in self.acting_players:
                if len(diner[player]):
                    Narrator().add([player.name, 'eats', player.his, format_list(diner[player]), self.current_area.at])
                    if poison[player] is not None:
                        Narrator().new([f'the {poison[player].name}', 'is', 'poisonous!'])
                        Narrator().cut()
                    player.consume_antidote()

    def loot_start(self):
        for player in self.acting_players:
            player.loot_start()
