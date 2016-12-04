from setuptools import setup

setup(
    name = 'lazycred',
    version = '0.2.2',
    description = 'Minimalistic Credentials Manager based on AWS.',
    author = 'Val Tenyotkin',
    author_email = 'val@tenyotk.in',
    url = 'https://github.com/2deviant/LazyCred',
    download_url = 'https://github.com/2deviant/LazyCred/tarball/0.2.2',
    packages = ['lazycred'],
    keywords = ['aws', 'kms', 'encryption', 'credentials', 'secret'],
    scripts = ['bin/lazycred'],
    classifiers = []
)
