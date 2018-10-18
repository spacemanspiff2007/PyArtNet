import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyartnet",
    version="0.5.0",
    author="spaceman_spiff",
    #author_email="",
    description="Python wrappers for the Art-Net protocol to send DMX over Ethernet",
    keywords = 'DMX, Art-Net, ArtNet',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/spacemanspiff2007/PyArtNet",
    packages=setuptools.find_packages(exclude=['tests']),
    python_requires='>=3.6',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
)