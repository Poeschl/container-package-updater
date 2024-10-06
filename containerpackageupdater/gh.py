import logging

import git
from github import Github


def reset_to_main_branch():
  repo = git.Repo('.')
  repo.git.checkout('main')
  repo.git.reset('--hard', 'origin/main')


def commit_file_to_new_branch(branch_name: str, file_path: str, commit_message: str):
  repo = git.Repo('.')
  if branch_name in repo.heads:
    raise ValueError(f'Branch {branch_name} already exists.')
  repo.git.checkout('HEAD', b=branch_name)
  repo.index.add([file_path])
  repo.index.commit(commit_message)
  logging.info(f'Created branch {branch_name} and committed changes.')


def push_branch(branch_name: str):
  repo = git.Repo('.')
  repo.git.push('origin', branch_name)


def create_pull_request(token: str, repo_name: str, branch_name: str, title: str, body: str):
  g = Github(token)
  repo = g.get_repo(repo_name)
  pr = repo.create_pull(title=title, body=body, head=branch_name, base='main')
  pr.set_labels('dependencies')
  logging.info(f'Created pull request {pr.number} for branch {branch_name}')
