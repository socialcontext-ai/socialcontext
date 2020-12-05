from setuptools import setup
import os

VERSION = '0.1.1'


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'README.md'),
        encoding='utf8',
    ) as fp:
        return fp.read()


from setuptools.command.install import install
from setuptools.command.develop import develop


class CommandMixin(object):
    """From: https://stackoverflow.com/a/53833930"""
    user_options = [
        ('deploy=', None, 'Set deploy to a different name'),
        ('secrets=', None, 'Set secrets to a different name'),
    ]

    def initialize_options(self):
        super().initialize_options()
        # Initialize options
        self.deploy = None
        self.secrets = None

    def finalize_options(self):
        # Validate options
        super().finalize_options()

    def run(self):
        # Use options
        global deploy
        global secrets
        if self.deploy is not None:
            deploy = self.deploy
        else:
            deploy = 'deploy'
        if self.secrets is not None:
            secrets = self.secrets
        else:
            secrets = 'secrets'
        super().run()


class InstallCommand(CommandMixin, install):
    user_options = getattr(install, 'user_options', []) + CommandMixin.user_options

class DevelopCommand(CommandMixin, develop):
    user_options = getattr(develop, 'user_options', []) + CommandMixin.user_options


setup(
    # This is an attempt to make the command names customizable but the approach
    # is not working. Despite being marked as global variables above, they
    # do not seem to be available here for the entry points value.
    #cmdclass={
    #    'install': InstallCommand,
    #    'develop': DevelopCommand,
    #},
    name='socialcontext',
    description='socialcontext.ai API client',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    author='Scott B. Bradley',
    url='https://github.com/socialcontext-ai/socialcontext',
    project_urls={
        'Issues': 'https://github.com/socialcontext-ai/socialcontext/issues',
        'Changelog': 'https://github.com/socialcontext-ai/socialcontext/blob/master/Changelog.md'
    },
    license='',
    version=VERSION,
    packages=[''],
    entry_points="""
        [console_scripts]
        socialcontext=socialcontext.cli:run
    """,
    install_requires=[
        'cryptography',
        'requests-oauthlib',
        'python-dotenv',
        'pydantic',
        'rich',
        'typer',
    ],
    extras_require={
        'test': ['pytest']
    },
    tests_require=['socialcontext[test]'],
)
