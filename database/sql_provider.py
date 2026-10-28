import os


class SQLProvider:
    """Загружает все SQL-файлы из папки и выдает текст запроса по имени файла."""

    def __init__(self, file_path):
        self.scripts = {}
        for file in os.listdir(file_path):
            with open(os.path.join(file_path, file), encoding='utf-8') as f:
                self.scripts[file] = f.read()

    def get(self, file):
        return self.scripts[file]
