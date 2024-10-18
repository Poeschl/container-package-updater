import logging
import re
from abc import ABC, abstractmethod
from typing import List

import requests

from containerpackageupdater.models import Package


class PackageManagerHandler(ABC):

  @abstractmethod
  def extract_packages(self, containerfile_content: str) -> List[Package]:
    pass

  @abstractmethod
  def find_online_updates(self, os_version: str, package_name: str, architectures: List[str]) -> List[Package]:
    pass

  @abstractmethod
  def update_package_in_containerfile(self, containerfile_content: str, package: Package, latest_package: Package) -> str:
    pass


class ApkPackageManager(PackageManagerHandler):

  def extract_packages(self, containerFile_content: str) -> list:
    pattern = r'RUN apk add .*\s+((?:\\\n\s*|\'[^\']+\'\s*)+)'
    matches = re.findall(pattern, containerFile_content, re.MULTILINE)
    packages = set()
    for match in matches:
      for package in re.findall(r'\'([^\']+)\'', match):
        parts = package.split("=")
        packages.add(Package(name=parts[0], version=parts[1]))
    return list(packages)

  def find_online_updates(self, os_version: str, package_name: str, architectures: List[str]) -> List[Package]:
    packages = set()
    for architecture in architectures:
      try:
        version = self.fetch_latest_version_of_apk_package(os_version, package_name, architecture)
        packages.add(Package(name=package_name, version=version))
      except Exception as e:
        logging.error(f'Failed to fetch package info for {package_name} on {architecture}: {e}')
    return list(packages)

  def fetch_latest_version_of_apk_package(self, alpine_version: str, package_name: str, architecture: str) -> str:
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
        raise Exception(f'Failed to fetch package info from main and community: {response.status_code} - {response.text}')

    match = re.search(r'<th class="header">Version</th>\s*<td>\s*(?:<strong>)?([^<\s]+)(?:</strong>)?\s*</td>', response.text)
    response.close()
    if not match:
      raise Exception(f'Could not find version info for package "{package_name}"')

    return match.group(1)

  def update_package_in_containerfile(self, containerfile_content: str, package: Package, latest_package: Package) -> str:
    return containerfile_content.replace(f'{package.name}={package.version}', f'{package.name}={latest_package.version}')


class AptGetPackageManager(PackageManagerHandler):

  def extract_packages(self, container_file_content: str) -> list:
    pattern = r'RUN apt-get .*?install((?:\s+\\?\s*[\w\d\-+.:~=]+)+)'
    matches = re.findall(pattern, container_file_content, re.MULTILINE)
    packages = set()
    for match in matches:
      for package in re.findall(r'(\w[\w\d+\-.:]*)=([\w\d:.\-+~]+)', match):
        packages.add(Package(name=package[0], version=package[1]))
    return list(packages)

  def find_online_updates(self, os_version: str, package_name: str, architectures: List[str]) -> List[Package]:
    packages = set()
    for architecture in architectures:
      try:
        version = self.get_debian_package_version(os_version, package_name, architecture)
        packages.add(Package(name=package_name, version=version))
      except Exception as e:
        logging.error(f'Failed to fetch package info for {package_name} on {architecture}: {e}')
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
