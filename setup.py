import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="efestoclient",
    version="0.0.9",
    author="Frederic Van Linthoudt",
    author_email="frederic.van.linthoudt@gmail.com",
    description="EfestoClient provides controlling Efesto heat devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fredericvl/efestoclient",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
