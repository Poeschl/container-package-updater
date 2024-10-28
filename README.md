# Container Package Updater

It will scan a Containerfile and suggest updates for the packages in it.

Currently supported package managers:

- `apk` (Alpine Linux)
- `apt-get` (Debian packages)

## Usage

The package updater is intended to be used as a action which runs regularly to create update PRs.
To do this use the following example on how to integrate it into your workflow.

There are some notes here:

* You need to have at least the permission to write content and create PRs
* The fetch-depth needs to be set to zero to get a full checkout
* To make a commit a git user needst to be set up. You can use any user here.

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
