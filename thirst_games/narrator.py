from typing import List


class Narrator:
    def __init__(self):
        self.current_sentence: List[str] = []
        self.text: List[List[str]] = []

    def tell(self):
        self.text.append(self.current_sentence)
        self.current_sentence = []
        while len(self.text):
            line = self.text.pop()
            line_str = ''
            for e in line:
                line_str += e
            print(line_str)

    def add(self, sentence):
        if isinstance(sentence, list):
            self.current_sentence.extend(sentence)
        else:
            self.current_sentence.append(sentence)

    def new(self, sentence):
        if len(self.current_sentence):
            self.text.append(self.current_sentence)
        self.current_sentence = []
        self.add(sentence)
