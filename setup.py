from setuptools import setup, find_packages
import pathlib

# Read requirements from requirements.txt
BASE_DIR = pathlib.Path(__file__).parent
with open(BASE_DIR / "requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="flipkart_product_recommender",
    version="0.1.0",
    description="Interactive flipkart product recommender",
    author="Your Name",
    packages=find_packages(),
    install_requires=requirements,
    extras_require={
        "dev": ["pytest", "black", "isort"]
    }
)