import spacy


def test_nlp_sentence_span():
    nlp = spacy.blank("en")

    # Test 1: Create a simple sentence and see how it gets tokenized by the
    # default tokenizer
    text = "Text1 text2 text3"
    doc = nlp(text)

    tokens = text.split()
    assert tokens == [x.text for x in doc]
    assert doc.char_span(0, 5, "LABEL1").text == tokens[0]
    assert doc.char_span(6, 11, "LABEL1").text == tokens[1]
    assert doc.char_span(12, 17, "LABEL1").text == tokens[2]
    assert doc.char_span(6, 17, "LABEL1").text == f"{tokens[1]} {tokens[2]}"

    # Test 2: Create a simple HTML element and see how it gets tokenized
    # default tokenizer
    text = ("<span style=\"font-family:Helvetica,sans-serif;font-size:9pt\">"
            "Page 1 of 2</span>")
    doc = nlp(text)
    assert [x.text for x in doc] == [
        '<',
        'span',
        'style="font',
        '-',
        'family',
        ':',
        'Helvetica',
        ',',
        'sans',
        '-',
        'serif;font',
        '-',
        'size:9pt">Page',  # This token won't let find the char_span
        '1',
        'of',
        '2</span',  # This token won't let find the char_span
        '>'
    ]

    search = "Page 1 of 2"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "LABEL1") is None

    # Test 3: Create a simple HTML element and see how it gets tokenized
    # default tokenizer. Now that we get tokens for 'Page', '1', 'of', '2', the
    # char_span method returns the span
    text = ("<span style=\"font-family:Helvetica,sans-serif;font-size:9pt\">"
            " Page 1 of 2 (count)")
    doc = nlp(text)
    assert [x.text for x in doc] == [
        '<',
        'span',
        'style="font',
        '-',
        'family',
        ':',
        'Helvetica',
        ',',
        'sans',
        '-',
        'serif;font',
        '-',
        'size:9pt',
        '"',
        '>',
        'Page',
        '1',
        'of',
        '2',
        '(',
        'count',
        ')'
    ]

    search = "Page 1 of 2"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "LABEL1").text == search


def test_nlp_sentence_span_with_html_tokenizer():
    from ner_classifier.html_tokenizer import (
        HTMLTokenizer2,
    )
    #  nlp = spacy.blank("en")
    #  nlp.tokenizer = create_html_tokenizer()(nlp)
    nlp = spacy.blank("en")
    nlp.tokenizer = HTMLTokenizer2(nlp.vocab)

    # Test 1: Create a simple HTML element and see how it gets tokenized
    # default tokenizer
    """
    text = ("<br/><link rel=\"inline-style\" href=\"url\"/>"
            "<span style=\"font-family:Helvetica,sans-serif;font-size:9pt\">"
            "Page 1 of 2</span>")
    """
    text = ("<span style=\"font-family:Helvetica,sans-serif;font-size:9pt\">"
            "Page 1 of 2</span>")
    doc = nlp(text)

    search = "Page 1 of 2"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "LABEL1").text == search

    # Test 2: Test proper HTML file
    nlp = spacy.blank("en")
    #  nlp.tokenizer = create_html_tokenizer()(nlp)
    nlp.tokenizer = HTMLTokenizer2(nlp.vocab)

    text = open("/home/hodei/.config/ner-classifier/djtalo85/Lloyds/documents/"
                "2017_February_Statement_1.html", "r").read()
    doc = nlp(text)

    search = "Page 1 of 2"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "LABEL1").text == search

    search = "24 October 2022"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "LABEL1").text == search

    search = "something is incorrect"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "LABEL1").text == search

    search = "Money In"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "LABEL1").text == search

    search = "2,679.71"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "LABEL1").text == search
