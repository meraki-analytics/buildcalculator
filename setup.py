#!/usr/bin/env python

import sys

from setuptools import setup, find_packages


install_requires = [
    "tabulate",
]

install_requires_via_github = [
    "https://github.com/meraki-analytics/cassiopeia"
]

setup(
    name="buildcalculator",
    version="0.1.1",
    author="Meraki Analytics, LLC",
    author_email="team@merakianalytics.com",
    url="https://github.com/meraki-analytics/cassiopeia",
    description="A Build Calculator for League of Legends",
    keywords=["LoL", "League of Legends", "Riot Games", "Build Calculator", "Sandbox"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Environment :: Web Environment",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Games/Entertainment",
        "Topic :: Games/Entertainment :: Real Time Strategy",
        "Topic :: Games/Entertainment :: Role-Playing",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    license="MIT",
    packages=find_packages(),
    zip_safe=True,
    install_requires=install_requires,
    dependency_links=install_requires_via_github
)
