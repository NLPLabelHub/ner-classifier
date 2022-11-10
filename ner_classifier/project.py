from json import load
from os import makedirs
from os.path import join, exists, basename
from tqdm import tqdm
import pickle
import requests
import spacy
from spacy.tokens import DocBin
import random
from spacy.util import minibatch
from spacy.training import Example
from .html_tokenizer import HTMLTokenizer


TRAIN_SPACY_DOC = "./train.spacy"
TRAIN_SPACY_MODEL = "./model.spacy"


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
        if not exists(TRAIN_SPACY_DOC):
            self.documents.create_training_data()
        if not exists(TRAIN_SPACY_MODEL):
            self.documents.train_model(iterations=30)


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
        nlp.tokenizer = HTMLTokenizer(nlp.vocab)
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

        db.to_disk(TRAIN_SPACY_DOC)

    def load_train_data(self):
        doc_bin = DocBin().from_disk(TRAIN_SPACY_DOC)
        train_data = []
        nlp = spacy.blank("en")
        nlp.tokenizer = HTMLTokenizer(nlp.vocab)
        for doc in doc_bin.get_docs(nlp.vocab):
            entities = []
            for ent in doc.ents:
                entities.append((ent.start_char, ent.end_char, ent.label_))

            spacy_entry = (doc.text, {"entities": entities})
            train_data.append(spacy_entry)
        return train_data

    def train_model(self, iterations):
        train_data = self.load_train_data()
        # Create the builtin NER pipeline
        nlp = spacy.blank("en")
        nlp.tokenizer = HTMLTokenizer(nlp.vocab)
        ner = nlp.add_pipe('ner')

        # Add labels
        for _, annotations in train_data:
            for ent in annotations['entities']:
                ner.add_label(ent[2])

        with nlp.disable_pipes(*[]):
            optimizer = nlp.begin_training()
            examples = []
            for text, annots in train_data:
                examples.append(Example.from_dict(nlp.make_doc(text), annots))
            nlp.initialize(lambda: examples)
            for i in range(iterations):
                random.shuffle(examples)
                losses = {}
                for batch in minibatch(examples, size=8):
                    nlp.update(
                        batch,
                        drop=0.2,        # droput - make it harder to memorise
                        sgd=optimizer,   # sgd    - callable to update weights
                        losses=losses)
                    print(losses)
        pickle.dump(nlp, open(TRAIN_SPACY_MODEL, "wb"))
        return nlp
