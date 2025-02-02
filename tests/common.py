import os
import pathlib
import shutil
import tempfile
import time
import unittest

import git


class CommonCase(unittest.TestCase):

    _settings = {
        "branch1": "15.0",
        "branch2": "16.0",
        "branch3": "17.0",
        "addon": "my_module",
        "from_org": None,
        "from_remote": None,  # We're testing locally without any remote
        "user_org": "OCA-test",
        "no_cache": True,
    }

    def setUp(self):
        # Create a temporary Git repository
        self.repo_path = self._create_tmp_git_repository()
        self.module_path = os.path.join(self.repo_path, self._settings["addon"])
        self.manifest_path = os.path.join(self.module_path, "__manifest__.py")
        self._fill_git_repository()

    def _create_tmp_git_repository(self):
        """Create a temporary Git repository to run tests."""
        repo_path = tempfile.mkdtemp()
        git.Repo.init(repo_path)
        return repo_path

    def _fill_git_repository(self):
        """Create branches with some content in the Git repository."""
        repo = git.Repo(self.repo_path)
        tpl_manifest_path = os.path.join(
            pathlib.Path(__file__).parent.resolve(),
            "data",
            "manifest.py",
        )
        with open(tpl_manifest_path) as tpl_manifest:
            tpl_manifest_lines = tpl_manifest.readlines()
        # Commit a file in '15.0'
        repo.git.checkout("--orphan", self._settings["branch1"])
        os.makedirs(self.module_path, exist_ok=True)
        with open(self.manifest_path, "w") as manifest:
            manifest.writelines(tpl_manifest_lines)
        repo.index.add(self.manifest_path)
        commit = repo.index.commit(f"[ADD] {self._settings['addon']}")
        # Port the commit from 'branch1' to 'branch2'
        repo.git.checkout("--orphan", self._settings["branch2"])
        repo.git.reset("--hard")
        # FIXME without a delay, both branches are targeting the same commit,
        # no idea why.
        time.sleep(1)
        repo.git.cherry_pick(commit.hexsha)
        # Create an empty 'branch3'
        repo.git.checkout("--orphan", self._settings["branch3"])
        repo.git.reset("--hard")
        repo.git.commit("-m", "Init", "--allow-empty")

    def _commit_change_on_branch(self, branch):
        """Commit a change that can be ported to another branch."""
        repo = git.Repo(self.repo_path)
        repo.git.checkout(branch)
        # Do some changes and commit
        with open(self.manifest_path, "r+") as manifest:
            content = manifest.read()
            content = content.replace('"base"', '"sale"')
            manifest.seek(0)
            manifest.write(content)
        repo.index.add(self.manifest_path)
        commit = repo.index.commit(f"[FIX] {self._settings['addon']}: fix dependency")
        return commit.hexsha

    def tearDown(self):
        # Clean up the Git repository
        shutil.rmtree(self.repo_path)
