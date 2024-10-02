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
