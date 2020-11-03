import typing
from pathlib import Path

import setuptools  # type: ignore


# Load version number without importing HABApp
def load_version() -> str:
    version: typing.Dict[str, str] = {}
    with open("pyartnet/__version__.py") as fp:
        exec(fp.read(), version)
    assert version['__version__'], version
    return version['__version__']


__version__ = load_version()

print(f'Version: {__version__}')
print('')

# When we run tox tests we don't have these files available so we skip them
readme = Path(__file__).with_name('readme.md')
long_description = ''
if readme.is_file():
    with readme.open("r", encoding='utf-8') as fh:
        long_description = fh.read()


setuptools.setup(
    name="pyartnet",
    version=__version__,
    author="spaceman_spiff",
    # author_email="",
    description="Python wrappers for the Art-Net protocol to send DMX over Ethernet",
    keywords='DMX, Art-Net, ArtNet',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/spacemanspiff2007/PyArtNet",
    packages=setuptools.find_packages(exclude=['tests']),
    python_requires='>=3.7',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
)
