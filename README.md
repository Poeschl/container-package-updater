# Container Package Updater

It will scan a Containerfile and suggest updates for the packages in it.

Currently supported package managers:

- `apk` (Alpine Linux)
- `apt-get` (Debian packages)

## Usage

### As python tool

// TBD

### As GitHub action

//TBD

Example:

```yaml
jobs:
  check-for-updates:
    name: Check for updates
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - name: ↩️ Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: 🔧 Set git bot user
        shell: bash
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com

      - name: 🚀 Run Updater
        uses: Poeschl/container-package-updater@main
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          containerFile: ContainerFile-apk
          osVersion: 3.18
          architectures: "x86_64, aarch64, armhf, armv7, x86"
```
