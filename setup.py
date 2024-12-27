from setuptools import find_packages, setup

setup(
    name="mmparser",
    version="0.9.6",
    description="Парсер megamarket.ru",
    author="xob0t",
    url="https://github.com/xob0t/mmparser",
    packages=find_packages(),
    install_requires=[
        "setuptools",
        "rich",
        "rich-argparse",
        "curl-cffi",
        "InquirerPy",
        "packaging",
    ],
    extras_require={
        "lxml": ["lxml"],
    },
    entry_points={"console_scripts": ["mmparser = core.main:main"]},
)
