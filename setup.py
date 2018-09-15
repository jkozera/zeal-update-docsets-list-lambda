import os
from setuptools import setup

setup(
    name="zevdocs-update-docsets-lambda",
    version="0.0.1",
    author="Jerzy Kozera",
    author_email="jerzy.kozera@gmail.com",
    description=("An AWS Lambda utility to update ZevDocs docsets list"),
    license="MIT",
    url="https://zevdocs.io",
    packages=['update_docsets'],
    install_requires=['boto3', 'paramiko', 'requests', 'dulwich'],
)
