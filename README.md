# Confluence Uploader

Template-based, CSV feeded mass-creation for and upload of articles to Confluence. 

## Installation

**Important:** Run the scripts provided in `scripts` from that directory.

### Installing Python
Python 3.10 is required. Here is a manual for [installing Python](https://realpython.com/installing-python/) on different operating systems. Additionally, the package manager `pip` is needed. Usually, it is already provided with a standard installation, but in case it is not, you need to install it [manually](https://pypi.org/project/pip/).

Depending on your operating system and file association configuration, the `python` command may be `python3` and `pip` may be `pip3`.

### Installing the required modules

You can install the required modules in multiple ways:
* On Windows, run `scripts/install.bat`
* On Linux, run `scripts/install.sh`
* Alternatively, install the required modules listed in `requirements.txt` via `pip install -r requirements.txt`
* ... or manually

It it recommended to generate an API token on Confluence, which, together with an username, then can be used for authentication with this program.

### Starting the program

* Run `python start.py` in the root directory.
* Alternatively, use `scripts/run.bat` or `scripts/run.sh`.

### Minimal configuration

The configuration properties in `config/config.ini` and `config/uploader_config.ini` contain explanatory comments. Consult those in case you're not sure about the meaning of specific configuration properties.

#### GUI Mode

If you're using the default configuration, you will configure the program via a GUI. This GUI will show you which properties are required.

#### Console Mode

If you're not using the GUI (set `user_gui` in `config/config.ini` to `false`), then you have to configure the program manually via `config/uploader_config.ini`.
The following properties have to be specified:
* `base_url`
* `template_id`
* `upload_space`
* and `data_csv`.
The other properties use default values.

### Documentation

* A short manual and an error catalog can be found at [./docs/manual.md](./docs/manual.md). Most errors in the program are logged with an error ID, which you can lookup in the error catalog for an explanation.
* Contact the author via `florian-f.haas@msg.group` if questions not covered by existing documentation arise.

### Dev installation

* If you want to run the supplied unit tests, you need the additional requirements specified in `test/requirements-test.txt`. You can install them via `pip install -r requirements.txt`.
* Alternatively, install them via `scripts/install-dev.bat` or `scripts/install-dev.sh`.

### Testing

* Modules excluded from test coverage measurement are `logger.py`, `gui.py`, `start.py` and `constants.py`, as well as everything in the `./test/` folder.
* `# pragma: no cover` comments tell the coverage tool to ignore the marked statement/body.
* You can run the tests manually or via `run-tests.bat`/`run-tests.sh` in `scripts`.

## LICENSE

MIT License

Copyright (c) 2022 msg systems ag

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
