from setuptools import setup, find_packages

setup(
    name='app-org',
    version='0.1',
    py_modules=find_packages(),
    install_requires=[
        'Click',
        'airspeed >= 0.4.2dev-20131111'
    ],
    entry_points='''
        [console_scripts]
        app-org=app_org.app_org:cli
    ''',
)
