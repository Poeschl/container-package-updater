import argparse
import logging
import re
import sys


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


def main(container_file: str):
  container_file_content = read_containerfile(container_file)

  packages = []

  if 'apk add' in container_file_content:
    packages = extract_apk_packages(container_file_content)

  logging.info(f'Found {len(packages)} apk packages in {container_file}')
  logging.debug('Detected packages:')
  for package in packages:
    logging.debug(f'{package}')

  return 0


if __name__ == '__main__':
  logging.basicConfig(level=logging.DEBUG,
                      format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
                      datefmt="%Y-%m-%d %H:%M:%S",
                      stream=sys.stdout)
  logging.info('Init docker package updater')

  parser = argparse.ArgumentParser(description='Docker Package Updater')
  parser.add_argument('--containerfile', required=True, help='The container file to check')
  args = parser.parse_args()

  exit(main(args.containerfile))
