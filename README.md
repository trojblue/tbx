# unibox

unibox is a tool that aims to provide a unified interface for various common daily operations.

## Features

**CLI**:
- `unibox resize <dir>`: resizes a directory of images using either `pillow` or `libvips`

**utils**:
- `UniLogger`: uniformed logger class
- `UniLoader`: uniformed data loader class

## Install

install from pypi:
```bash
pip install unibox
```

build from source:
```bash
git clone https://github.com/trojblue/unibox

# pip install poetry
poetry install
poetry build
pip install dist/unibox-<version number>.whl
```
