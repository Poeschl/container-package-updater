import logging

import git
from git import RemoteReference
from github import Github


def setup_workspace_repository(repo_path: str):
  repo = git.Repo(repo_path)
  # set git repo path as trustworthy
  repo.config_writer(config_level='global').set_value('safe', 'directory', repo_path)
  # fetch all git branches
  repo.remote().fetch(prune=True)


def reset_to_main_branch(repo_path: str):
  repo = git.Repo(repo_path)
  repo.heads.main.checkout()
  repo.remote().pull()


def exists_branch(repo_path: str, branch_name: str) -> bool:
  repo = git.Repo(repo_path)
  remote_branch_list = list(map(lambda remote_ref: remote_ref.name.removeprefix('origin/'), repo.remote().refs))
  logging.debug(f'Existing remote branches: {remote_branch_list}')
  return branch_name in remote_branch_list


def create_branch_from_main(repo_path: str, branch_name: str):
  repo = git.Repo(repo_path)
  new_current = repo.create_head(branch_name, 'main')
  new_current.checkout(force=True)
  logging.info(f'Created branch {branch_name}.')


def checkout_branch(repo_path: str, branch_name: str):
  repo = git.Repo(repo_path)
  if branch_name in repo.heads:
    # Local branch
    logging.debug(f'Checkout local branch {branch_name}')
    repo.heads[branch_name].checkout()
  else:
    logging.debug(f'Checkout remote branch {branch_name}')
    repo.remote().refs[branch_name].checkout(force=True, b=branch_name)


def rebase_branch_to_main(repo_path: str, branch_name: str):
  repo = git.Repo(repo_path)
  repo.git.rebase('main', branch_name)
  logging.info(f'Rebased branch {branch_name} to main.')


def commit_file_to_current_branch(repo_path: str, file_path: str, commit_message: str):
  repo = git.Repo(repo_path)
  repo.index.add([file_path])
  repo.index.commit(commit_message)
  logging.info(f'Committed changes.')


def push_branch(repo_path: str, branch_name: str, force=False):
  repo = git.Repo(repo_path)
  repo.active_branch.set_tracking_branch(RemoteReference(repo, f"refs/remotes/origin/{branch_name}"))
  repo.remote().push(force=force).raise_if_error()
  logging.info(f'Pushed branch {branch_name} to origin. (forced={force})')


def create_pull_request(token: str, repo_name: str, branch_name: str, title: str, body: str):
  g = Github(token)
  repo = g.get_repo(repo_name)
  pr = repo.create_pull(title=title, body=body, head=branch_name, base='main')
  pr.set_labels('dependencies')
  logging.info(f'Created pull request {pr.number} for branch {branch_name}')


def update_pull_request(token: str, repo_name: str, branch_name: str, body: str):
  g = Github(token)
  repo = g.get_repo(repo_name)
  pr = repo.get_pulls(state='open', base='main', head=branch_name).get_page(0)[0]
  pr.edit(body=body)
  logging.info(f'Updated pull request {pr.number} for branch {branch_name}')
