from json import load
from os import makedirs
from os.path import join, exists, basename
from tqdm import tqdm
from time import sleep
import requests


class Project:
    def __init__(self, annotations_file, config_dir):
        self.config = load(open(annotations_file))
        self.user_name = self.config["user_name"]
        self.project_name = self.config["project_name"]
        config_dir = join(config_dir, "ner-classifier", self.user_name,
                             self.project_name)
        self.model_dir = config_dir
        self.documents = Documents(self.config["documents"], config_dir)


class Documents:
    def __init__(self, documents, config_dir):
        self.documents_dir = join(config_dir, "documents")
        makedirs(self.documents_dir, exist_ok=True)
        print("[*] Fetching documents...")
        for document in tqdm(documents):
            url = document["file"]
            filename = join(self.documents_dir, basename(url))
            if not exists(filename):
                with requests.get(url, stream=True) as req:
                    req.raise_for_status()
                    with open(filename, 'wb') as f:
                        for chunk in req.iter_content(chunk_size=8192):
                            f.write(chunk)
