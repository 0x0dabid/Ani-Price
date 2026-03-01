from setuptools import setup, find_packages

setup(
    name="ani-price",
    version="1.0.0",
    description="Token price tracker using DexScreener API",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "ani-price=ani_price.cli:main",
        ],
    },
)
