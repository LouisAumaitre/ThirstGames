from typing import List


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

    def switch(self, sentence: str) -> str:
        if sentence in self._switch:
            return self._switch[sentence]
        return sentence

    def tell(self):
        self.cut()
        while len(self.text):
            line = self.text.pop(0)
            if not len(line):
                continue
            line_str = ''
            for e in line:
                if e == ',':
                    line_str = line_str[:-1]
                line_str += self.switch(e) + ' '
            if line_str[-2] != '=':
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
