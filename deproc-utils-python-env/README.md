# deproc-utils-python-env

Python virtual environment utilities for
[deproc](https://github.com/gurveervirk/deproc): find a project's virtual
environment and list the packages installed in it.

## Install

```bash
python -m pip install deproc-utils-python-env
```

`deproc-utils-python-env` supports Python 3.10 and newer and has no dependencies.

## Usage

```python
from deproc.utils.python_env import (
    detect_venv,
    find_site_packages,
    list_installed_packages,
)

venv = detect_venv("/path/to/project")
if venv:
    site_packages = find_site_packages(venv)
    if site_packages:
        for package in list_installed_packages(site_packages):
            print(package.name, package.version, package.top_level_modules)
```

## API

- `detect_venv(base_path, config=None)` returns the absolute path of the first
  virtual environment it finds, checking in order `config["venv_path"]`, the
  `VIRTUAL_ENV` environment variable, and `<base_path>/.venv`. A directory counts
  as a virtual environment when it contains `pyvenv.cfg`. Returns `None` if none
  is found.
- `parse_pyvenv_cfg(venv_path)` returns the `key = value` pairs of `pyvenv.cfg`
  as a dict, or `{}` if the file is missing.
- `find_site_packages(venv_path)` returns the `lib/python*/site-packages`
  directory of a virtual environment, or `None`.
- `list_installed_packages(site_packages_path)` reads each `*.dist-info` entry
  and returns `PackageInfo` objects with `name`, `version`, `install_path`,
  `top_level_modules`, `editable_origin` (for an editable install, the path
  recorded in its `.pth` file, otherwise `None`) and `mtime`.
