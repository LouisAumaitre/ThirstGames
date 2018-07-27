from random import choice
from typing import List, Optional


def format_list(names: List[str]):
    names.sort()
    if len(names) == 1:
        return names[0]
    out = ''
    for i in range(len(names) - 2):
        out += names[i] + ', '
    out += names[-2] + ' and ' + names[-1]
    return out


class Narrator:
    def __init__(self):
        self.current_sentence: List[str] = []
        self.active_subject = ''
        self.text: List[List[str]] = []
        self._switch = {
            'at the ruins': 'in the ruins',
            'at the plain': 'in the plain',
            'at the jungle': 'in the jungle',
            'at the forest': 'in the forest',
            'at the hill': 'on the hill',
        }
        self.kill_word = {
            'axe': ['decapitates'],
            'sword': ['decapitates'],
            'knife': ['stabs'],
            'trident': ['stabs'],
            'spear': ['stabs'],
            'bare hands': ['strangle'],
            'club': ['knocks'],
        }
        for key, value in self.kill_word.items():
            value.append('kills')

    def switch(self, phrase: str) -> str:
        if phrase in self._switch:
            return self._switch[phrase]
        return phrase

    def kill_switch(self, phrase: str, full_sentence: List[str]):
        if phrase == 'kills':
            tools = [word.split(' ')[-1] for word in full_sentence if word.startswith('with ')]
            if len(tools) == 1:
                tool = tools[0]
                if tool in self.kill_word:
                    return choice(self.kill_word[tool])
        return phrase

    def tell(self, filters: Optional[List[str]]=None):
        if filters is None:
            filters = []
        self.cut()
        while len(self.text):
            line = self.text.pop(0)
            if not len(line):
                continue
            line_str = ''
            for e in line:
                if e in filters:
                    continue
                if e == ',':
                    line_str = line_str[:-1]
                e = self.kill_switch(e, line)
                line_str += self.switch(e) + ' '
            if line_str[-2] not in ['=', '-', '.']:
                line_str = line_str[:-1] + '.'
            print(line_str)

    def add(self, sentence):
        if isinstance(sentence, list):
            # avoid repetition of subject
            if sentence[0] == self.active_subject:
                sentence[0] = 'and'
            else:
                self.active_subject = sentence[0]
                if len(self.current_sentence) and self.current_sentence[-1] != 'and':
                    self.comma()

            # avoid repetition of tool
            tool = [e for e in sentence if e.startswith('with')]
            if tool and (tool[0] in self.current_sentence
                         or tool[0].replace('his', 'her') in self.current_sentence
                         or tool[0].replace('her', 'his') in self.current_sentence):
                sentence.remove(tool[0])

            # avoid repetition of place
            place = [e for e in sentence if e.startswith('at')]
            if place and place[0] in self.current_sentence:
                sentence.remove(place[0])

            # avoid repetition of verb
            if len(sentence) > 1 and sentence[1] in sentence and sentence[1] in self.current_sentence and \
                            sentence[0] == 'and':
                sentence.remove(sentence[1])

            self.current_sentence.extend(sentence)
        else:
            self.current_sentence.append(sentence)

    def comma(self):
        if len(self.current_sentence):
            self.current_sentence.append(',')

    def cut(self):
        if len(self.current_sentence):
            self.text.append(self.current_sentence)
        self.current_sentence = []
        self.active_subject = ''

    def new(self, sentence):
        self.cut()
        self.add(sentence)

    def replace(self, old, new):
        for i in range(len(self.current_sentence)):
            if self.current_sentence[i] == old:
                self.current_sentence[i] = new

    def remove(self, to_remove):
        self.current_sentence.remove(to_remove)
