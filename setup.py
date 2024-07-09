from setuptools import find_packages, setup

setup(
    name='mmparser',
    version='0.6.3',
    description='Парсер megamarket.ru',
    author='xob0t',
    url='https://github.com/xob0t/mmparser',
    packages=find_packages(),
    install_requires=[
        'rich',
        'curl-cffi',
        'InquirerPy',
    ],
    extras_require={
        'lxml': ['lxml'],
    },
    entry_points={
        'console_scripts': ['mmparser = core.main:main']
    },
)
