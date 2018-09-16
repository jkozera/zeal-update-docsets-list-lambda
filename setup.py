import os
from setuptools import setup, find_packages

setup(
    name="zevdocs-update-docsets-lambda",
    version="0.0.1",
    author="Jerzy Kozera",
    author_email="jerzy.kozera@gmail.com",
    description=("An AWS Lambda utility to update ZevDocs docsets list"),
    license="MIT",
    url="https://zevdocs.io",
    packages=find_packages(),
    install_requires=['boto3', 'paramiko', 'requests', 'dulwich'],
)
