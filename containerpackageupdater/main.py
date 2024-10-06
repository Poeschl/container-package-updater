import argparse
import logging
import os
import sys

from containerpackageupdater.gh import reset_to_main_branch, commit_file_to_new_branch, push_branch, create_pull_request
from containerpackageupdater.models import Package
from containerpackageupdater.package_manager_handler import ApkPackageManager, PackageManagerHandler


def read_containerfile(file_path: str) -> str:
  with open(file_path, 'r') as file:
    return file.read()


def write_containerfile(file_path: str, content: str):
  with open(file_path, 'w') as file:
    file.write(content)


def update_single_version(package: Package, latest_package: Package, container_file: str, package_manager: PackageManagerHandler, container_file_content: str,
                          push_repository: str, token: str, dry_run: bool):
  logging.info(f'Package "{package.name}" is outdated. Current version: {package.version}, latest version: {latest_package.version}')

  reset_to_main_branch()
  updated_content = package_manager.update_package_in_containerfile(container_file_content, package, latest_package)
  write_containerfile(container_file, updated_content)
  change_name = f':arrow_up: Update {package.name} to version {latest_package.version}'
  branch_name = f'containerfile-dependency/{package.name}'
  try:
    commit_file_to_new_branch(branch_name, container_file, change_name)
    push_branch(branch_name)

    pr_body = "| Package Name | Current Version | Latest Version |\n"
    pr_body += "|--------------|-----------------|----------------|\n"
    pr_body += f"| {package.name} | {package.version} | {latest_package.version} |\n"
    if not dry_run:
      create_pull_request(token, push_repository, branch_name, change_name, pr_body)
    else:
      logging.info(f"Would have created a PR for {package.name} -> {latest_package.version}")
  except ValueError:
    logging.info('Skipping update for package. Already exists in a PR.')


def main(token: str, dry_run: bool, container_file: str, push_repository: str, os_version: str, architectures: list[str]) -> int:
  reset_to_main_branch()

  container_file_content = read_containerfile(container_file)

  packages = []
  package_manager: PackageManagerHandler = None

  if 'apk add' in container_file_content:
    logging.info('Detected apk package manager')
    package_manager = ApkPackageManager()

  packages = package_manager.extract_packages(container_file_content)

  logging.info(f'Found {len(packages)} packages in {container_file}')
  logging.debug('Detected packages:')
  for package in packages:
    logging.debug(f'{package}')

    latest_packages = package_manager.find_online_updates(os_version, package.name, architectures)
    if len(latest_packages) == 1:
      latest_package = latest_packages[0]
      if package.version != latest_package.version:
        update_single_version(package, latest_package, container_file, package_manager, container_file_content, push_repository, token, dry_run)
      else:
        logging.info(f'Package "{package.name}" is up to date.')
    elif len(latest_packages) > 1:
      logging.warning(f'Found multiple versions for package for multiple architectures: {latest_packages}\nSkipping update.')

  return 0


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", stream=sys.stdout)

  parser = argparse.ArgumentParser(description='Docker Package Updater')
  parser.add_argument('--token', required=True, help='The GitHub token to use for PR creation')
  parser.add_argument('--containerFile', required=True, help='The container file to check')
  parser.add_argument('--repository', required=False, help='The repository update PRs should be created in', default=os.environ.get('GITHUB_REPOSITORY'))
  parser.add_argument('--osVersion', required=False, help='The os version to use for the version check. Example "3.18" for alpine', default=3.18)
  parser.add_argument('--architecture', required=False, help='The architectures to check. (Comma seperated in string)', default=['x86_64'], action='append')
  parser.add_argument('--dryRun', required=False, help='If true, no PR is created.', default=False)

  args = parser.parse_args()

  exit(main(args.token, args.dryRun, args.containerFile, args.repository, args.osVersion, args.architecture))
