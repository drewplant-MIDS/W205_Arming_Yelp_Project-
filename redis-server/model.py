from gensim.models.doc2vec import Doc2Vec

class ModelLoader:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        mod = Doc2Vec.load(self.path)
        return mod

    def __exit__(self, a,b,c):
        pass

