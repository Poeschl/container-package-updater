import argparse
import logging
import sys

from dockerpackageupdater.package_manager_handler import ApkPackageManager, PackageManagerHandler


def read_containerfile(file_path: str) -> str:
  with open(file_path, 'r') as file:
    return file.read()


def main(container_file: str, os_version: str, architectures: list[str]) -> int:
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
