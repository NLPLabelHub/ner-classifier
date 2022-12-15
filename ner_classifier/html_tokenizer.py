import re
import logging
import spacy
from spacy.tokens import Doc
from html.parser import HTMLParser
from html import unescape


# The HTML codes can be either:
#   - Named (&apos;)
#   - Decimal (&#39;)
#   - Hexadecimal (&#x27;)
#
# See: https://www.howtocreate.co.uk/sidehtmlentity.html
# Min/max values {2,8} and {2,4} where infered from the above page.
HTML_CODE = re.compile(r"^&[a-zA-Z]{2,8};|^&#x?[a-z0-9]{2,4};")


def get_real_token(text, token):
    """
    Given a text and a token which might have already unescaped special symbols
    (&, ', £, ...) find the escaped symbols (&amps;, &apos;, &pound;).
    """
    real_token = ""
    text_index = 0
    for char in token:
        match = HTML_CODE.search(text[text_index:])
        if match:
            compare_text = match.group()
        else:
            compare_text = text[text_index:text_index + 1]
        if unescape(compare_text) == char:
            real_token += compare_text
            text_index = text_index + len(compare_text)
        else:
            raise Exception(f"Token {char} couldn't be found in "
                            f"{text[text_index:100]}")
    return real_token


class HTMLTokenParser(HTMLParser):
    def __init__(self, nlp, *args, **kwargs):
        super().__init__(*args, **kwargs, convert_charrefs=False)
        self.tokens = []
        self.nlp = nlp

    def feed(self, string):
        self.tokens = []
        self.spaces = []
        self.line_number = 0
        super().feed(string)
        return self.tokens, self.spaces

    def update_tokens(self, tokens, spaces):
        self.tokens.extend(tokens)
        self.spaces.extend(spaces)
        self.line_number += sum([len(x) for x in tokens]) + \
            sum([bool(x) for x in spaces])
        assert len(self.tokens) == len(self.spaces)

    def handle_starttag(self, tag, attrs):
        logging.debug("Handle startag: %s, (%s)", tag, attrs)
        self.update_tokens(["<", tag], [False, bool(attrs)])
        for index, attr in enumerate(attrs):
            self.update_tokens(
                [f"{attr[0]}", "=", "\""], [False, False, False])
            if attr[0] == "style":
                styles = attr[1].split(";")
                for style in styles:
                    if not style:
                        continue
                    words = style.split(":")
                    self.update_tokens(
                        [words[0], ":", words[1]], [False, False, False])
                    self.update_tokens([";"], [False])
                # Only remove last semicolon if actually the code doesn't have
                # any semicolons at the end
                if attr[1].strip()[-1] != ";":
                    token = self.tokens.pop()  # Remove last semicolon
                    self.line_number -= len(token)
                    space = self.spaces.pop()  # Remove last semicolon
                    if space:
                        self.line_number -= 1

            else:
                self.update_tokens([attr[1]], [False])
            self.update_tokens(["\""], [index < len(attrs) - 1])
        self.update_tokens([">"], [False])

    def handle_endtag(self, tag):
        logging.debug("Handle endtag: %s", tag)
        self.update_tokens(["</", tag, ">"], [False, False, False])

    def handle_data(self, data):
        logging.debug("Handle data: '%s'", data)
        doc = self.nlp(data)
        for token in doc:
            self.update_tokens([token.text], [token.whitespace_])
        assert len(self.tokens) == len(self.spaces)

    def handle_comment(self, data):
        self.update_tokens(["<", data, ">"], [False, False, False])

    def handle_entityref(self, name):
        data = unescape(f"&{name};")
        token = get_real_token(self.rawdata[self.line_number:], data)
        self.update_tokens([token], [False])

    def handle_charref(self, name):
        if name.startswith('x'):
            data = chr(int(name[1:], 16))
        else:
            data = chr(int(name))
        token = get_real_token(self.rawdata[self.line_number:], data)
        self.update_tokens([token], [False])

    def handle_decl(self, data):
        self.update_tokens(["<!", data, ">"], [False, False, False])


class HTMLTokenizer:
    def __init__(self, vocab):
        self.vocab = vocab
        self.pyparser = HTMLTokenParser(spacy.blank("en"))

    def __call__(self, string):
        words, spaces = self.pyparser.feed(string)
        if len(words) != len(spaces):
            raise Exception("Different amount of words and spaces")
        # Avoid zero-length tokens
        for i, word in enumerate(words):
            if word == "":
                words[i] = " "
                spaces[i] = False
        return Doc(self.vocab, words=words, spaces=spaces)
