import argparse
import logging
import re
import sys
from enum import Enum

import requests


class Package:
  def __init__(self, name: str, version: str):
    self.name = name
    self.version = version

  def __eq__(self, other):
    return self.name == other.name and self.version == other.version

  def __hash__(self):
    return hash((self.name, self.version))

  def __str__(self):
    return f'{self.name} {self.version}'


class PackageManager(Enum):
  APK = 'APK'
  APT = 'APT'


def read_containerfile(file_path: str) -> str:
  with open(file_path, 'r') as file:
    return file.read()


def extract_apk_packages(dockerfile_content: str) -> list:
  pattern = r'RUN apk add .*\s+((?:\\\n\s*|\'[^\']+\'\s*)+)'
  matches = re.findall(pattern, dockerfile_content, re.MULTILINE)
  packages = set()
  for match in matches:
    for package in re.findall(r'\'([^\']+)\'', match):
      parts = package.split("=")
      packages.add(Package(name=parts[0], version=parts[1]))
  return list(packages)


def fetch_latest_version_of_apk_package(alpine_version: str, package_name: str, architecture: str) -> str:
  if alpine_version is None:
    raise ValueError('Alpine version is required to check for the latest package version')

  url = f'https://pkgs.alpinelinux.org/package/v{alpine_version}/main/{architecture}/{package_name}'
  response = requests.get(url)

  if response.status_code != 200:
    response.close()
    # Try community repository
    url = f'https://pkgs.alpinelinux.org/package/v{alpine_version}/community/{architecture}/{package_name}'
    response = requests.get(url)

    if response.status_code != 200:
      raise Exception(f'Failed to fetch package info from main and community: {response.status_code}')

  match = re.search(r'<th class="header">Version</th>\s*<td>\s*([^<\s]+)\s*</td>', response.text)
  response.close()
  if not match:
    raise Exception(f'Could not find version info for package "{package_name}"')

  return match.group(1)


def get_online_packages(alpine_version: str, package_name: str, architecures: list[str]) -> list:
  packages = set()
  for architecture in architecures:
    try:
      version = fetch_latest_version_of_apk_package(alpine_version, package_name, architecture)
      packages.add(Package(name=package_name, version=version))
    except Exception as e:
      logging.error(f'Failed to fetch package info for {package_name} on {architecture}: {e}')
  return list(packages)


def main(container_file: str, alpine_version: str, architectures: list[str]) -> int:
  container_file_content = read_containerfile(container_file)

  packages = []
  manager_type = None

  if 'apk add' in container_file_content:
    manager_type = PackageManager.APK

  if manager_type == PackageManager.APK:
    packages = extract_apk_packages(container_file_content)

  logging.info(f'Found {len(packages)} apk packages in {container_file}')
  logging.debug('Detected packages:')
  for package in packages:
    logging.debug(f'{package}')
    if manager_type == PackageManager.APK:

      latest_packages = get_online_packages(alpine_version, package.name, architectures)
      if len(latest_packages) == 1:
        latest_package = latest_packages[0]
        if package.version != latest_package.version:
          logging.info(f'Package "{package.name}" is outdated. Current version: {package.version}, latest version: {latest_package.version}')
        else:
          logging.info(f'Package "{package.name}" is up to date.')
      elif len(latest_packages) > 1:
        logging.warning(f'Found multiple versions for package for multiple architectures: {latest_packages}')

  return 0


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO,
                      format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
                      datefmt="%Y-%m-%d %H:%M:%S",
                      stream=sys.stdout)
  logging.info('Init docker package updater')

  parser = argparse.ArgumentParser(description='Docker Package Updater')
  parser.add_argument('--containerFile', required=True, help='The container file to check')
  parser.add_argument('--alpineVersion', required=False, help='The alpine version to use for the version check', default=3.18)
  parser.add_argument('--architecture', required=False, help='The architectures to check. (Comma seperated in string)', default=['x86_64'], action='append')

  args = parser.parse_args()

  exit(main(args.containerFile, args.alpineVersion, args.architecture))
