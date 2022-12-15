import spacy


def test_get_real_token():
    from ner_classifier.html_tokenizer import get_real_token

    garbage_text = "asdlkfjas &amp;' 4444 &#x27; &pound; sldfkja sldkjf alsjdf"
    # Test & symbol was found correctly in the text
    text = "&amp;"
    assert get_real_token(text + garbage_text, token="&") == text
    # Test 'S symbol was found correctly in the text
    text = "SAINSBURY&apos;S"
    assert get_real_token(text + garbage_text, token="SAINSBURY'S") == text
    # Test &'4444'£ symbol was found correctly in the text
    # Notice that in the original text the first ' wasn't escaped and the 2nd
    # one was escaped with a special code
    text = "&amp;'4444&#x27;&pound;"
    assert get_real_token(text + garbage_text, token="&'4444'£") == text


def test_html_tokenizer():
    """
    This tests that the tokenizer deals well with the below situations:
        - The first style has a list of attributes and the last one finishes
          with semicolon, whereas the rest of the stlyes don't finish with
          semicolon.
        - There is a Balance statement with a £ symbol escaped. The tokenizer
          is able to find the right token.
        - The tokenizer is able to properly extract the Blance, Date and the
          Description.
    """

    from ner_classifier.html_tokenizer import HTMLTokenizer
    # Test 1: Test proper HTML file
    nlp = spacy.blank("en")
    nlp.tokenizer = HTMLTokenizer(nlp.vocab)

    text = """
    <p style="white-space:pre;margin:0;padding:0;top:329pt;left:537pt;">
    <span style="font-size:.05pt;color:#ffffff">Balance (&#xa3;)</span></p>
    <p style="white-space:pre;margin:0;padding:0;top:329pt;left:497pt">
    <span style="font-size:9pt">236.69</span>
    <span style="font-size:.05pt;color:#ffffff">.</span></p>
    <p style="white-space:pre;margin:0;padding:0;top:354pt;left:57pt">
    <span style="font-size:.05pt;color:#ffffff">Date</span></p>
    <p style="white-space:pre;margin:0;padding:0;top:354pt;left:57pt">
    <span style="font-size:9pt">25 Sep 17</span>
    <span style="font-size:.05pt;color:#ffffff">.</span></p>
    <p style="white-space:pre;margin:0;padding:0;top:354pt;left:122pt">
    <span style="font-size:.05pt;color:#ffffff">Description</span></p>
    <p style="white-space:pre;margin:0;padding:0;top:354pt;left:122pt">
    <span style="font-size:9pt">SAINSBURY&apos;S S/MKT</span>
    <span style="font-size:.05pt;color:#ffffff">.</span></p>
    """
    doc = nlp(text)

    assert str(doc) == text

    search = "236.69"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "BALANCE").text == search

    search = "25 Sep 17"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "DATE").text == search

    search = "SAINSBURY&apos;S S/MKT"
    ann = []
    ann.append(text.index(search))
    ann.append(ann[0] + len(search))
    assert doc.char_span(ann[0], ann[1], "DESCRIPTION").text == search
