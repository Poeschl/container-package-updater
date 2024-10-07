import argparse
import logging
import os
import sys

from containerpackageupdater.gh import reset_to_main_branch, push_branch, create_pull_request, exists_branch, \
  checkout_branch, commit_file_to_current_branch, rebase_branch_to_main, update_pull_request
from containerpackageupdater.models import Package
from containerpackageupdater.package_manager_handler import ApkPackageManager, PackageManagerHandler


def read_containerfile(file_path: str) -> str:
  with open(file_path, 'r') as file:
    return file.read()


def write_containerfile(file_path: str, content: str):
  with open(file_path, 'w') as file:
    file.write(content)


def update_single_version(package: Package, latest_package: Package, container_file: str, package_manager: PackageManagerHandler, container_file_content: str,
                          push_repository: str, token: str, dry_run: bool, repo_path: str):
  logging.info(f'Package "{package.name}" is outdated. Current version: {package.version}, latest version: {latest_package.version}')

  branch_name = f'containerfile-dependency/{package.name}'
  update_branch = exists_branch(repo_path, branch_name)

  if not dry_run:
    checkout_branch(repo_path, branch_name, not update_branch)
    if update_branch:
      rebase_branch_to_main(repo_path, branch_name)

  updated_content = package_manager.update_package_in_containerfile(container_file_content, package, latest_package)
  write_containerfile(repo_path + '/' + container_file, updated_content)
  change_name = f':arrow_up: Update {package.name} to version {latest_package.version}'
  try:
    if not dry_run:
      commit_file_to_current_branch(repo_path, repo_path + '/' + container_file, change_name)
      push_branch(repo_path, branch_name, force=update_branch)

      pr_body = "| Package Name | Current Version | Latest Version |\n"
      pr_body += "|--------------|-----------------|----------------|\n"
      pr_body += f"| {package.name} | {package.version} | {latest_package.version} |\n"

      if update_branch:
        update_pull_request(token, push_repository, branch_name, pr_body)
      else:
        create_pull_request(token, push_repository, branch_name, change_name, pr_body)
    else:
      logging.info(f"Would have created a PR for {package.name} -> {latest_package.version}")
  except ValueError:
    logging.info('Skipping update for package. Already exists in a PR.')


def main(token: str, dry_run: bool, repo_path: str, container_file: str, push_repository: str, os_version: str, architectures: list[str]) -> int:
  if not dry_run:
    reset_to_main_branch(repo_path)

  container_file_content = read_containerfile(repo_path + '/' + container_file)

  packages = []
  package_manager: PackageManagerHandler = None

  if 'apk add' in container_file_content:
    logging.info('Detected apk package manager')
    package_manager = ApkPackageManager()

  if package_manager is None:
    logging.error("No supported package manager could be found. Exiting")
    return 2

  packages = package_manager.extract_packages(container_file_content)

  logging.info(f'Found {len(packages)} packages in {repo_path}/{container_file}')
  logging.debug('Detected packages:')
  for package in packages:
    logging.debug(f'{package}')

    latest_packages = package_manager.find_online_updates(os_version, package.name, architectures)
    if len(latest_packages) == 1:
      latest_package = latest_packages[0]
      if package.version != latest_package.version:
        update_single_version(package, latest_package, container_file, package_manager, container_file_content, push_repository, token, dry_run, repo_path)
      else:
        logging.info(f'Package "{package.name}" is up to date.')
    elif len(latest_packages) > 1:
      logging.warning(f'Found multiple versions for package for multiple architectures: {latest_packages}\nSkipping update.')

  return 0


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", stream=sys.stdout)

  parser = argparse.ArgumentParser(description='Docker Package Updater')
  parser.add_argument('--token', required=True, help='The GitHub token to use for PR creation')
  parser.add_argument('--containerFile', required=True, help='The container file to check. Relative to "--repositoryWorkspace"')
  parser.add_argument('--repositoryWorkspace', required=False, help='The folder of the repository holding the container file.', default='.')
  parser.add_argument('--repository', required=False, help='The repository update PRs should be created in', default=os.environ.get('GITHUB_REPOSITORY'))
  parser.add_argument('--osVersion', required=False, help='The os version to use for the version check. Example "3.18" for alpine', default=3.18)
  parser.add_argument('--architectures', required=False, help='The architectures to check. (Comma-separated list)', default='x86_64', type=str)
  parser.add_argument('--dryRun', help='If set, no PR is created.', default=False, action='store_true')

  args = parser.parse_args()
  parsed_architectures = []
  if args.architectures is not None:
    args.architectures: str
    parsed_architectures = [s.strip() for s in args.architectures.split(",")]

  exit(main(args.token, args.dryRun, args.repositoryWorkspace, args.containerFile, args.repository, args.osVersion, parsed_architectures))
