from json import load
from os import makedirs
from os.path import join, exists, basename
from tqdm import tqdm
import requests
import spacy
from spacy.tokens import DocBin
from .html_tokenizer import HTMLTokenizer2


class Project:
    def __init__(self, annotations_file, config_dir):
        self.config = load(open(annotations_file))
        self.user_name = self.config["user_name"]
        self.project_name = self.config["project_name"]
        config_dir = join(config_dir, "ner-classifier", self.user_name,
                          self.project_name)
        self.model_dir = config_dir
        self.documents = Documents(self.config["documents"], config_dir)
        self.documents.fetch_documents()
        self.documents.create_training_data()


class Documents:
    def __init__(self, documents, config_dir):
        self.documents = documents
        self.config_dir = config_dir
        self.documents_dir = join(config_dir, "documents")
        makedirs(self.documents_dir, exist_ok=True)

    def fetch_documents(self):
        print("[*] Fetching documents...")
        for document in tqdm(self.documents):
            url = document["file"]
            filename = join(self.documents_dir, basename(url))
            if not exists(filename):
                with requests.get(url, stream=True) as req:
                    req.raise_for_status()
                    with open(filename, 'wb') as f:
                        for chunk in req.iter_content(chunk_size=8192):
                            f.write(chunk)

    def create_training_data(self):
        print("[*] Creating training data")
        nlp = spacy.blank("en")
        nlp.tokenizer = HTMLTokenizer2(nlp.vocab)
        db = DocBin()
        for document in tqdm(self.documents):
            url = document["file"]
            print(url)
            filename = join(self.documents_dir, basename(url))
            text = open(filename, "r").read()
            doc = nlp(text)
            ents = []
            for annotation in document["annotations"]:
                span = doc.char_span(
                    annotation["html_offset_start"],
                    annotation["html_offset_end"],
                    label=annotation["label"])
                # If span is not found, it might be that the selection contains
                # special symbols that need to escaped.
                if span is None:
                    selection = nlp.tokenizer.escape_selection(
                        annotation["html_offset_start"],
                        annotation["selection"])
                    span = doc.char_span(
                        annotation["html_offset_start"],
                        annotation["html_offset_start"] + len(selection),
                        label=annotation["label"])
                    if span is None:
                        raise Exception(f"Annotation {annotation} cannot be "
                                        f"found in HTML document. Stopping "
                                        f"training")
                ents.append(span)
            doc.ents = ents
            db.add(doc)

        db.to_disk("./train.spacy")
