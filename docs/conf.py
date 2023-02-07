import os
import re
import sys

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'PyArtNet'
copyright = '2023, spacemanspiff2007'
author = 'spacemanspiff2007'


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx_exec_code',
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints',
]

templates_path = ['_templates']
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']


# -- Options for exec code -------------------------------------------------
exec_code_working_dir = '../src'
exec_code_source_folders = ['../src', '../tests']


# -- Options for autodoc -------------------------------------------------
autodoc_member_order = 'bysource'
autoclass_content = 'class'

# required for autodoc
sys.path.insert(0, os.path.join(os.path.abspath('..'), 'src'))


# -- Options for exec code -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None)
}


# -- Options for nitpick -------------------------------------------------
# Don't show warnings for missing python references since these are created via intersphinx
nitpick_ignore_regex = [
    (re.compile(r'py:data|py:class'), re.compile(r'typing\..+')),
]
