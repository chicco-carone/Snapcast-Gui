from setuptools import setup, find_packages
from snapcast_gui.misc.snapcast_gui_variables import SnapcastGuiVariables

setup(
    name="snapcast-gui",
    version=SnapcastGuiVariables.snapcast_gui_version,
    packages=find_packages(),
    py_modules=["main"],
    install_requires=["PySide6", "snapcast", "platformdirs", "notify_py"],
    author="Francesco",
    author_email="chiccocarone@gmail.com",
    description="A gui to manage and control snapcast",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/chicco-carone/Snapcast-Gui",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    entry_points={
        "gui_scripts": ["snapcast-gui = main:main"]
    },
)
