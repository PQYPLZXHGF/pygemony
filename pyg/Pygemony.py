from fnmatch import filter
from os import walk, path
import hashlib

from utils import detect_mimetype
from github import GithubAPIManager
from languages import *


class Pygemony:
    def __init__(self, user=None, token=None, owner=None, repo=None):
        # todo_found contains a list of the following layout:
        # ['file_path', 'line_number', 'todo_message', 'md5 of todo']
        self.todo_found = []
        self.github = GithubAPIManager(user, token, owner, repo)
        # TODO(ian): Add support for parsing more than one file type
        self.language = self.lookup_language()

    def find_end_comment(self, f):
        # TODO(ian): Remove this function as we no longer support multiline TODO
        todo_content = []
        x = f
        count = 0
        for line in x.readlines():
            todo_content.append(line)
            if self.language.multi_comment[1] in line:
                return todo_content

            if count > 20:
                return None

            todo_content.append(line)
            count += 1

    def _sanitize_todo_line(self, lines):
        # We're mainly aiming to remove newlines and tab characters here.
        lines = lines.replace('\n', '')
        while '    ' in lines or '\t' in lines:
            lines = lines.replace('    ', '')
        for lang in self.language:
            lines = lines.replace(lang.single_comment, '')
        return lines

    @staticmethod
    def hash_todo(todo_content):
        m = hashlib.md5()
        m.update(todo_content)
        return str(m.hexdigest())

    def parse_for_todo(self, f, file_):
        for i, line in enumerate(f.readlines()):
            if "TODO" in line:
                line = self._sanitize_todo_line(line)
                self.todo_found.append([file_, i, line, self.hash_todo(line)])

    def parse_by_extension(self, files):
        for lang in self.language:
            for ext in lang.file_exts:
                for file_ in filter(files, ext):
                    yield file_

    def find_all_files(self, root):
        files_found = []
        for roots, dirs, files in walk(root):
            for file_ in self.parse_by_extension(files):
                files_found.append(path.join(roots, file_))
        return files_found

    def file_handler(self):
        # First we need to remove any non-text files
        files_found = self.find_all_files('./')
        # TODO(ian): filter() over files to parse out by mimetype
        for file_ in files_found:
            file_type = detect_mimetype(file_)
            # We're looking for startswith('text/'). Mimetype returns
            # None if it can't determine file type. Remove if either is True
            if file_type[0].startswith("application") or file_type[0] is None:
                files_found.remove(file_)

        for file_ in files_found:
            try:
                with open(file_, 'r') as f:
                    self.parse_for_todo(f, file_)
            except IOError as e:
                print "Failed to open file {} with error of {}".format(file_, e)

        return files_found

    def run(self):
        self.file_handler()
        self.github.commit(self.todo_found)

    def lookup_language(self):
        lang_map = {'cpp': LanguageCPP,
                    'python': LanguagePython,
                    'javascript': LanguageJavascript,
                    'c': LanguageC}
        langs = [i for i in self.github.get_languages()]
        return [lang_map[str(langs[0][0]).lower()]()]
