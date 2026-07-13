from setuptools import find_packages, setup

with open("frappe_ai_hiring/__init__.py") as f:
	version_line = [line for line in f if line.startswith("__version__")][0]
	version = version_line.split('"')[1]

setup(
	name="frappe_ai_hiring",
	version=version,
	description="AI-Driven Hiring Automation System for Frappe HRMS",
	author="Connection Loops",
	author_email="ashutosh@connectionloops.com",
	license="MIT",
	packages=find_packages(),
	include_package_data=True,
	python_requires=">=3.10",
	install_requires=[],
	classifiers=[
		"Development Status :: 4 - Beta",
		"Framework :: Frappe",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: MIT License",
		"Programming Language :: Python :: 3.10",
		"Programming Language :: Python :: 3.11",
		"Programming Language :: Python :: 3.12",
	],
)
