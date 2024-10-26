class Package:

  def __init__(self, name: str, version: str, repository: str = None, os_version_overwrite: str = None):
    self.name = name
    self.version = version
    self.repository = repository
    self.os_version_overwrite = os_version_overwrite

  def __eq__(self, other):
    return self.name == other.name and self.version == other.version

  def __hash__(self):
    return hash((self.name, self.version))

  def __str__(self):
    return f'{self.name} {self.version}'
