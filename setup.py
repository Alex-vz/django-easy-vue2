# -*- coding: utf-8 -*-
import setuptools
#import easy_vue

"""
with open("README.rst", "r") as fh:
    long_description = fh.read()
"""

setuptools.setup(
    name="django-easy-vue2", # Replace with your own username
    version="0.0.3",
    author="Alex V Zobov",
    author_email="alex_ins@mail.ru",
    description="Easy integration Vue.js and Django",
    long_description="long_description",
    #long_description_content_type="text/x-rst",
    url="https://github.com/Alex-vz/django-easy-vue2",
    keywords='Django vue.js JavaScript',
    #packages=setuptools.find_packages(),
    #packages=["easy_vue",],
    packages=setuptools.find_packages(include=["easy_vue", "easy_vue.*",]),
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: JavaScript',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',    
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Django :: 1.9",
        "Natural Language :: English",
        "Natural Language :: Russian",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: User Interfaces",
    ],
    python_requires=">2.7,<3.0",
)