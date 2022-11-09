import re
import logging
import spacy
from spacy.tokens import Doc
from html.parser import HTMLParser
from html.entities import name2codepoint
from html import escape, unescape
from bs4.dammit import EntitySubstitution


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
        super().__init__(*args, **kwargs)
        self.tokens = []
        self.nlp = nlp
        # Unfortunately I didn't find a single library that escapes all
        # characters at once. Hence using 2 different escape methods
        # html_escape: Scapes characters such as "'"
        # html.escape("&'4444'£")  => '&amp;&#x27;4444&#x27;£'
        self.html_escape = escape
        # bs4_escape: Scapes special symbols such as "£"
        # bs4_escape("&'4444'£")  => "&amp;'4444'&pound;"
        self.bs4_escape = EntitySubstitution().substitute_html

    def replace_special_symbols(self, data):
        # The below transformation is not perfect but if the original data is
        # different to the transformation, then certainly there could be a
        # special html symbol or entity
        # - data = "&'4444'£"
        # - self.html_escape(data) => '&amp;&#x27;4444&#x27;£'
        #   Notice that the £ symbol wasn't escaped yet.
        # - self.bs4_escape(self.html_escape(data)) =>
        #           '&amp;amp;&amp;#x27;4444&amp;#x27;&pound;'
        #   Notice that the & symbol was escaped again. so the above result
        #   cannot be unescaped to get back to the original data. However,
        #   after those 2 transformations we know that the data had symbols
        #   that can be escaped, which is good enough.
        can_be_escaped = self.bs4_escape(self.html_escape(data)) != data
        if can_be_escaped:
            start_index = sum([len(x) for x in self.tokens]) + \
                sum([bool(x) for x in self.spaces])
            return get_real_token(self.string[start_index:], data)
        else:
            return data

    def escape_selection(self, start_pos, data):
        """
        In some cases, where the annotation selection contains special symbols,
        they have to be found in the HTML text with the right symbols.

        For instance the whole annotation "SAINSBURY'S S/MKT" might not exist
        in the HTML, but "SAINSBURY&apos;S S/MKT" exists. Hence, we need to
        return the string as it is found in the HTML.
        """
        text = self.string[start_pos:]
        real_selection = ""
        doc = self.nlp(data)
        for token in doc:
            real_selection += get_real_token(text, token.text)
            if token.whitespace_:
                real_selection += token.whitespace_
            text = self.string[start_pos + len(real_selection):]
        return real_selection

    def feed(self, string):
        self.string = string
        self.tokens = []
        self.spaces = []
        super().feed(string)
        return self.tokens, self.spaces

    def handle_starttag(self, tag, attrs):
        logging.debug("Handle startag: %s, (%s)", tag, attrs)
        self.tokens.extend(["<", tag])
        self.spaces.extend([False, bool(attrs)])
        assert len(self.tokens) == len(self.spaces)
        for index, attr in enumerate(attrs):
            self.tokens.extend([f"{attr[0]}", "=", "\""])
            self.spaces.extend([False, False, False])
            assert len(self.tokens) == len(self.spaces)
            if attr[0] == "style":
                styles = attr[1].split(";")
                for style in styles:
                    if not style:
                        continue
                    words = style.split(":")
                    self.tokens.extend([words[0], ":", words[1]])
                    self.spaces.extend([False, False, False])
                    assert len(self.tokens) == len(self.spaces)
                    self.tokens.extend([";"])
                    self.spaces.extend([False])
                # Only remove last semicolon if actually the code doesn't have
                # any semicolons at the end
                if attr[1].strip()[-1] != ";":
                    self.tokens.pop()  # Remove last semicolon
                    self.spaces.pop()  # Remove last semicolon

            else:
                self.tokens.append(attr[1])
                self.spaces.extend([False])
                assert len(self.tokens) == len(self.spaces)
            self.tokens.extend(["\""])
            self.spaces.extend([index < len(attrs) - 1])
        self.tokens.extend([">"])
        self.spaces.extend([False])
        assert len(self.tokens) == len(self.spaces)

    def handle_endtag(self, tag):
        logging.debug("Handle endtag: %s", tag)
        self.tokens.extend(["</", tag, ">"])
        self.spaces.extend([False, False, False])
        assert len(self.tokens) == len(self.spaces)

    def handle_data(self, data):
        logging.debug("Handle data: '%s'", data)
        doc = self.nlp(data)
        for token in doc:
            self.tokens.append(self.replace_special_symbols(token.text))
            self.spaces.append(token.whitespace_)
        assert len(self.tokens) == len(self.spaces)

    def handle_comment(self, data):
        self.tokens.extend(["<", data, ">"])
        self.spaces.extend([False, False, False])
        assert len(self.tokens) == len(self.spaces)

    def handle_entityref(self, name):
        breakpoint()
        c = chr(name2codepoint[name])
        print("Named ent:", c)

    def handle_charref(self, name):
        breakpoint()
        if name.startswith('x'):
            c = chr(int(name[1:], 16))
        else:
            c = chr(int(name))
        print("Num ent  :", c)

    def handle_decl(self, data):
        self.tokens.extend(["<!", data, ">"])
        self.spaces.extend([False, False, False])
        assert len(self.tokens) == len(self.spaces)


class HTMLTokenizer:
    def __init__(self, vocab):
        self.vocab = vocab
        self.pyparser = HTMLTokenParser(spacy.blank("en"))

    def escape_selection(self, start_index, data):
        return self.pyparser.escape_selection(start_index, data)

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
