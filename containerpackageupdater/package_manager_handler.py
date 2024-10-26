import logging
import re
from abc import ABC, abstractmethod
from typing import List

import requests

from containerpackageupdater.gh import push_branch
from containerpackageupdater.models import Package


class PackageManagerHandler(ABC):

  @abstractmethod
  def extract_packages(self, containerfile_content: str) -> List[Package]:
    pass

  @abstractmethod
  def find_online_updates(self, os_version: str, package: Package, architectures: List[str]) -> List[Package]:
    pass

  @abstractmethod
  def update_package_in_containerfile(self, containerfile_content: str, package: Package, latest_package: Package) -> str:
    pass


class ApkPackageManager(PackageManagerHandler):

  def extract_packages(self, containerFile_content: str) -> list:
    pattern = r'RUN apk add (.*\s+(?:\\\n\s*|["\'][^"\']+["\']\s*)+)'
    matches = re.findall(pattern, containerFile_content, re.MULTILINE)
    packages = set()
    for match in matches:
      repository = None
      if '/community' in match:
        repository = 'community'

      os_version_overwrite = None
      if '/edge' in match:
        os_version_overwrite = "edge"

      for package in re.findall(r'(\w[\w\d+\-.:]*)=(\d[\w\d:.\-+~]+)', match):
        packages.add(Package(name=package[0], version=package[1], repository=repository, os_version_overwrite=os_version_overwrite))
    return list(packages)

  def find_online_updates(self, os_version: str, package: Package, architectures: List[str]) -> List[Package]:
    packages = set()
    for architecture in architectures:
      try:
        version = self.fetch_latest_version_of_apk_package(os_version, package, architecture)
        packages.add(Package(name=package.name, version=version))
      except Exception as e:
        logging.error(f'Failed to fetch package info for {package.name} on {architecture}: {e}')
    return list(packages)

  def fetch_latest_version_of_apk_package(self, alpine_version: str, package: Package, architecture: str) -> str:
    if alpine_version is None:
      raise ValueError('Alpine version is required to check for the latest package version')

    alpine_version_for_package = f"v{alpine_version}"
    if package.os_version_overwrite is not None:
      alpine_version_for_package = package.os_version_overwrite

    repository_for_package = "main"
    if package.repository is not None:
      repository_for_package = package.repository

    trys_left = 1
    while trys_left >= 0:
      url = f'https://pkgs.alpinelinux.org/package/{alpine_version_for_package}/{repository_for_package}/{architecture}/{package.name}'
      response = requests.get(url)

      if response.status_code != 200:
        response.close()
        # Try community repository
        repository_for_package = "community"
        logging.info(f"Retry update check in community repository for {package.name} ")
        trys_left -= 1
      else:
        trys_left = 0

    if response.status_code != 200:
      raise Exception(f'Failed to fetch package info from main and community: {response.status_code} - {response.text}')

    match = re.search(r'<th class="header">Version</th>\s*<td>\s*(?:<strong>)?([^<\s]+)(?:</strong>)?\s*</td>', response.text)
    response.close()
    if not match:
      raise Exception(f'Could not find version info for package "{package.name}"')

    return match.group(1)

  def update_package_in_containerfile(self, containerfile_content: str, package: Package, latest_package: Package) -> str:
    return containerfile_content.replace(f'{package.name}={package.version}', f'{package.name}={latest_package.version}')


class AptGetPackageManager(PackageManagerHandler):

  def extract_packages(self, container_file_content: str) -> list:
    pattern = r'RUN apt-get .*?install((?:\s+\\?\s*(?:[\w\d\-+.:~=]+|["\'][\w\d\-+.:~=]+["\']))+)'
    matches = re.findall(pattern, container_file_content, re.MULTILINE)
    packages = set()
    for match in matches:
      for package in re.findall(r'(\w[\w\d+\-.:]*)=(\d[\w\d:.\-+~]+)', match):
        packages.add(Package(name=package[0], version=package[1]))
    return list(packages)

  def find_online_updates(self, os_version: str, package: Package, architectures: List[str]) -> List[Package]:
    packages = set()
    for architecture in architectures:
      try:
        version = self.get_debian_package_version(os_version, package.name, architecture)
        packages.add(Package(name=package.name, version=version))
      except Exception as e:
        logging.error(f'Failed to fetch package info for {package.name} on {architecture}: {e}')
    return list(packages)

  def get_debian_package_version(self, os_version: str, package_name: str, architecture: str) -> str:

    # Use the Debian Tracker API to get package information
    url = f"https://packages.debian.org/{os_version}/{package_name}"
    response = requests.get(url)

    if response.status_code != 200:
      raise Exception(f"Failed to retrieve package information: {response.status_code}")

    match = re.search(r'<h1>Package:.* \((.*)\)', response.text)

    if not match:
      raise Exception(f'Could not find version info for package "{package_name}"')

    version = match.group(1)

    if 'others' in version:
      logging.info("Use per-architecture version")
      match = re.search(r'<th><a href="[^"]+">' + architecture + '</a></th>\\s*<td class=\'vcurrent\'>([\\d.]+-[^<]+)</td>', response.text)
      version = match.group(1)

    response.close()
    return version

  def update_package_in_containerfile(self, containerfile_content: str, package: Package, latest_package: Package) -> str:
    return containerfile_content.replace(f'{package.name}={package.version}', f'{package.name}={latest_package.version}')
