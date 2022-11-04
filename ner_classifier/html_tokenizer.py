import logging
import spacy
from spacy.tokens import Doc
from html.parser import HTMLParser
from html.entities import name2codepoint


class HTMLTokenParser(HTMLParser):
    def __init__(self, nlp, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tokens = []
        self.nlp = nlp
        self.special_symbol_starts = "&#x"
        self.special_symbols = False

    def replace_special_symbols(self, data):
        if not self.special_symbols:
            return data

        # Currencies and Special Symbols to Hex UTF-8
        data = data.replace("&", "&#x26;")
        data = data.replace("%", "&#x25;")
        data = data.replace("#", "&#x23;")
        data = data.replace("$", "&#x24;")
        data = data.replace("£", "&#xa3;")
        data = data.replace("+", "&#x2b;")
        data = data.replace("~", "&#x7e;")
        data = data.replace("•", "&#x95;")
        data = data.replace("·", "&#xb7;")
        # Bullet "•", &#x95;
        # Middle Dot, Georgian Comma "·", &#xb7;
        data = data.replace("\xc3\xb7", "&#xf7;")

        # The usual accented characters for Modern and Middle French
        data = data.replace("À", "&#xc0;")
        data = data.replace("Ç", "&#xc7;")
        data = data.replace("É", "&#xc9;")
        data = data.replace("Ö", "&#xd6;")
        data = data.replace("Ÿ", "&#x9f;")
        data = data.replace("à", "&#xe0;")
        data = data.replace("â", "&#xe2;")
        data = data.replace("ç", "&#xe7;")
        data = data.replace("è", "&#xe8;")
        data = data.replace("é", "&#xe9;")
        data = data.replace("ê", "&#xea;")
        data = data.replace("ë", "&#xeb;")
        data = data.replace("î", "&#xee;")
        data = data.replace("ï", "&#xef;")
        data = data.replace("ô", "&#xf4;")
        data = data.replace("ö", "&#xf6;")
        data = data.replace("ù", "&#xf9;")
        data = data.replace("û", "&#xfb;")
        data = data.replace("ÿ", "&#xff;")
        data = data.replace("œ", "&#x9c;")
        data = data.replace("ü", "&#xfc;")

        # The older WORD6 renderings of French accents with REMark just before
        # ç c cedilla just below this REMark, which shows as &#x2021;
        data = data.replace("‡", "&#xe7;")
        # &#x201a;  é just below this REM
        data = data.replace("‚", "&#xe9;")
        # ï &#65533;
        data = data.replace("‹", "&#xef;")
        #  y diaeresis   une diérèse
        data = data.replace("˜", "&#xff;")
        #  a grave:
        data = data.replace("…", "&#xe0;")
        #  u diaeresis
        data = data.replace("\x81", "&#xfc;")
        #  e grave:
        data = data.replace("Š", "&#xe8;")
        #  u grave
        data = data.replace("—", "&#xf9;")
        #  e diaeresis
        data = data.replace("‰", "&#xeb;")
        return data

    def feed(self, string):
        self.special_symbols = self.special_symbol_starts in string
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
                    words = style.split(":")
                    self.tokens.extend([words[0], ":", words[1]])
                    self.spaces.extend([False, False, False])
                    assert len(self.tokens) == len(self.spaces)
                    self.tokens.extend([";"])
                    self.spaces.extend([False])
                if styles:
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
        self.tokens.extend([self.replace_special_symbols(x.text) for x in doc])
        self.spaces.extend([x.whitespace_ for x in doc])
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


class HTMLTokenizer2:
    def __init__(self, vocab):
        self.vocab = vocab
        self.nlp = spacy.blank("en")

    def __call__(self, string):
        # http://www.pizan.lib.ed.ac.uk/python/xtirp8.py
        self.pyparser = HTMLTokenParser(self.nlp)
        words, spaces = self.pyparser.feed(string)
        if len(words) != len(spaces):
            raise Exception("Different amount of words and spaces")
        # Avoid zero-length tokens
        for i, word in enumerate(words):
            if word == "":
                words[i] = " "
                spaces[i] = False
        return Doc(self.vocab, words=words, spaces=spaces)
