import setuptools

setuptools.setup(
    name='otlogging',
    version='0.0.1',
    description='Tools to log or interpret logs for OpenTrons protocols',
    url='https://github.com/luigiferiani/OTlogging.git',
    author='Luigi Feriani',
    author_email='l.feriani@lms.mrc.ac.uk',
    license='MIT',
    packages=setuptools.find_packages(),
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'run_opentrons_simulation=otlogging.run_opentrons_simulation:main',
            'parse_robot_log=otlogging.parse_robot_log:main',
            ]
        },
    )
