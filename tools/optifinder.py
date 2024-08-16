from typing import List, Dict


class OptiFinder:
    def __init__(self, words: List[str]) -> None:
        self.words = words
        self.word_count = len(self.words)

    def search_around(self, source: Dict[str, str], index: int = 0):
        word = self.words[index]
        multiword_max_count = 1
        multiword_candidate: str | None = None
        for slug in source:
            if slug == word or source[slug] == word:
                return slug, 1
            this_words = source[slug].split()
            this_word_count = len(this_words)
            if this_word_count > multiword_max_count and index + this_word_count <= self.word_count:
                i = this_word_count - 1
                while i >= 0 and self.words[index + i] == this_words[i]:
                    i -= 1
                if i < 0:
                    multiword_max_count = this_word_count
                    multiword_candidate = slug

        return multiword_candidate, multiword_max_count
