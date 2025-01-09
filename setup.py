from setuptools import setup, find_packages

setup(
    name="confluence",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'selenium',
        'scrapy',
        # 其他依赖项...
    ],
) 