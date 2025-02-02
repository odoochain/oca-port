# Copyright 2022 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

import os
import re

import requests

from .git import PullRequest

GITHUB_API_URL = "https://api.github.com"


def request(url, method="get", params=None, json=None):
    """Request GitHub API."""
    headers = {"Accept": "application/vnd.github.groot-preview+json"}
    if os.environ.get("GITHUB_TOKEN"):
        token = os.environ.get("GITHUB_TOKEN")
        headers.update({"Authorization": f"token {token}"})
    full_url = "/".join([GITHUB_API_URL, url])
    kwargs = {"headers": headers}
    if json:
        kwargs.update(json=json)
    if params:
        kwargs.update(params=params)
    response = getattr(requests, method)(full_url, **kwargs)
    if not response.ok:
        raise RuntimeError(response.text)
    return response.json()


def get_original_pr(from_org: str, repo_name: str, branch: str, commit_sha: str):
    """Return original GitHub PR data of a commit."""
    gh_commit_pulls = request(
        f"repos/{from_org}/{repo_name}/commits/{commit_sha}/pulls"
    )
    gh_commit_pull = [
        data
        for data in gh_commit_pulls
        if (
            data["base"]["ref"] == branch
            and data["base"]["repo"]["full_name"] == f"{from_org}/{repo_name}"
        )
    ]
    return gh_commit_pull and gh_commit_pull[0] or {}


def search_migration_pr(from_org: str, repo_name: str, branch: str, addon: str):
    """Return an existing migration PR (if any) of `addon` for `branch`."""
    # NOTE: If the module we are looking for is named 'a_b' and the PR title is
    # written 'a b', we won't get any result, but that's better than returning
    # the wrong PR to the user.
    repo = f"{from_org}/{repo_name}"
    prs = request(
        f"search/issues?q=is:pr+is:open+repo:{repo}+base:{branch}+in:title++mig+{addon}"
    )
    for pr in prs.get("items", {}):
        # Searching for 'a' on GitHub could return a result containing 'a_b'
        # so we check the result for the exact module name to return a relevant PR.
        if _addon_in_text(addon, pr["title"]):
            return PullRequest(
                number=pr["number"],
                url=pr["html_url"],
                author=pr["user"]["login"],
                title=pr["title"],
                body=pr["body"],
            )


def _addon_in_text(addon, text):
    """Return `True` if `addon` is present in `text`."""
    return any(addon == term for term in re.split(r"\W+", text))
