try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

classifiers = [
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Libraries",
    "Topic :: Utilities",
    "Development Status :: 3 - Alpha",
    "Operating System :: OS Independent",
]

packages = [
    'wpapi',
]

with open("README.md", "r") as fp:
    long_description = fp.read()

setup(name="wpapi",
      version="0.0.2",
      author="Michael Tartre",
      author_email="mt@quantology.org",
      url="https://github.com/quantology/wpapi",
      packages=packages,
      install_requires=["mistune", "frontmatter", "requests"],
      description="Python WordPress API",
      long_description=long_description,
      long_description_content_type='text/markdown',
      license="Community Clause BSD-3",
      classifiers=classifiers
)
