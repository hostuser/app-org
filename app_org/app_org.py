#! /Usr/bin/python

import sys
import click
import airspeed
import shutil
import os
import ConfigParser
import collections

# --------------------------------------------------------------------------------------
# Helper functions and classes
class FakeSecHead(object):
    """Helper class to read sectionless property files using the python ConfigParser"""

    def __init__(self, fp):
        self.fp = fp
        self.sechead = '[nosection]\n'

    def readline(self):
        if self.sechead:
            try:
                return self.sechead
            finally:
                self.sechead = None
        else:
            return self.fp.readline()

def list_contains(list, item):
    """Checks whether a list contains an item"""

    if item in list:
        return True
    else:
        return False


def get_desc_id(desc_name):
    """Get filename without extension"""

    return os.path.splitext(desc_name)[0]


def has_tag(tag_list, tag):
    return tag in tag_list


def find_versions(path):
    """Helper function to parse a module directory located within an
    application repository structure, returning all versions of an
    application sorted by cluster.
    """
    versions = {}
    for root, dirs, files in os.walk(path):
        if len(files) > 0:
            cluster = os.path.basename(root).capitalize()
            versions[cluster] = sorted(files)

    return versions


def find_apps(path):
    """Helper function to get all app names from the specified application
    repository root folder
    """
    apps = [f for f in os.listdir(path)
            if os.path.isdir(os.path.join(path, f)) and f != '.git']

    return apps


def find_jobs(path):
    """Returns a sorted dictionary of jobname/job(object) for a
    specified path."""

    if os.path.isdir(path):
        dirs = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        jobs = {}
        for directory in dirs:
            j = Job(os.path.join(path, directory))
            jobs[j.id] = j

        return collections.OrderedDict(sorted(jobs.items()))
    else:
        return {}


def check_valid_apps(path, app_list):
    """Helper function to verify all apps in the list actually have
    a folder in the application repository.
    """
    all_apps = find_apps(path)
    common_apps = set(app_list).intersection(all_apps)
    not_valid_apps = set(app_list).difference(all_apps)

    return common_apps, not_valid_apps


def create_app_documentation(apprepo, apps, template, output_dir):

    for a in apps:
        md_text = apprepo.get_app(a).doc.create_doc_page(template)
        if not output_dir:
            click.echo(md_text)
        else:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            doc_file = os.path.join(output_dir, a + ".md")

            with open(doc_file, 'w') as text_file:
                text_file.write(md_text)


# --------------------------------------------------------------------------------------
# Exceptions
class ApplicationMissingException(Exception):
    pass


# --------------------------------------------------------------------------------------
# classes
class AppRepo(object):
    """Encapsulates an application repository structure"""

    def __init__(self, path):
        self.path = path
        apps = {}
        for app in find_apps(self.path):
            apps[app] = Application(self, app)

        # sort applications by name
        self.apps = collections.OrderedDict(sorted(apps.items(), key=lambda s: s[0].lower()))


    def check_valid_apps(self, apps):
        """Checks whether all the applications in the provided list are present

        :param apps: a list of app name strings
        :returns: a tupel with a Boolean value for whether all applications are availalbe, and a string message.
        """
        valid, not_valid = check_valid_apps(self.path, apps)

        if not_valid:
            return False, "Invalid applications: " + ', '.join(not_valid)
        else:
            return True, "All applications present"

    def get_app(self, app_name):
        result = self.apps[app_name]
        if not result:
            raise ApplicationMissingException("No application '{}' available in '{}".format(app_name, self.path))

        return result

    def create_summary_page(self, template):

        if type(template) is str:
            template = open(template, 'r')

        tmp_dir = '/tmp/app-org/summary'
        shutil.rmtree(tmp_dir, True)
        os.makedirs(tmp_dir)
        shutil.copy2(template.name, tmp_dir)
        loader = airspeed.CachingFileLoader(tmp_dir, True)

        template = loader.load_template(os.path.basename(template.name))
        properties = {}

        # helper functions
        properties['len'] = len
        properties['get_desc_id'] = get_desc_id
        properties['contains'] = list_contains
        properties['has_tag'] = has_tag

        properties['applications'] = self.apps

        result = template.merge(properties, loader=loader)
        return result



class Job(object):
    """Encapsulates the information located in a job directory (under
    [application]/jobs in an application repository structure).

    Properties to be used in a template:

    - id: the unique id of the job (name of the base directory)
    - path: the path to the base directory of the job
    - versions: dictionary of versions of the application this job
        will work with, sorted by cluster
    - tags: list of tags associated with this job
    - mdfiles: all names of existing *.md files in the base directory
    - job_descriptions: a dictionary of all *.sl files in the base
        directory, value is either a corresponding .md file (if
        exists) or 'None' if no such file exists
    - job_files_path: the path to the input files for this job
    - job_files: a list of all input files for this job, relative to
        job_files_path
    - properties:
        a dictionary with optional properties, populated by parsing an
        optional 'job.properties' file in the base
        directory. Important ones:
           - name: the 'pretty' name of the job
    """

    def __init__(self, path):
        self.path = path
        self.id = os.path.basename(path)
        self.properties = {}
        self.properties['name'] = self.id
        self.tags = {}
        self.versions = {}
        self.mdfiles = []
        self.job_descriptions = {}
        self.job_files_path = os.path.join(self.path, 'files')
        self.job_files = []
        self.job_properties_file = os.path.join(self.path, 'job.properties')

        if os.path.isfile(self.job_properties_file):
            Config = ConfigParser.SafeConfigParser()
            Config.readfp(FakeSecHead(open(self.job_properties_file)))
            for key, value in Config.items('nosection'):
                if key == 'versions':
                    self.versions['N/A'] = [str(value).strip() for value in value.split(',')]
                if key == 'tags':
                    self.tags = [str(value).strip() for value in value.split(',')]
                    self.properties[key] = self.tags
                else:
                    self.properties[key] = value

        md_files = [f for f in os.listdir(self.path) if f.endswith('.md')]
        for f in md_files:
            self.properties[f] = f
            self.mdfiles.append(f)

        sl_files = [f for f in os.listdir(self.path) if f.endswith('.sl')]
        for f in sl_files:
            self.properties[f] = f
            sl_id = get_desc_id(f)
            if os.path.isfile(os.path.join(self.path, sl_id + ".md")):
                self.job_descriptions[f] = sl_id + ".md"
            else:
                self.job_descriptions[f] = None

        for root, dirs, files in os.walk(self.job_files_path):
            for file in files:
                relative = root[len(self.job_files_path):]
                if relative:
                    self.job_files.append(relative[1:] + "/" + file)
                else:
                    self.job_files.append(file)

        self.job_files.sort()


# application class
class Application(object):
    """Class that encapsulates the information for a specific
    application within an application repository structure.

    Important properties:
      - name: the name of the application
      - path: the path to the base directory to this application
      - versions: a map of versions available for this application,
          sorted by cluster
      - doc: the doc object for this application
      - jobs: a dictionary of jobnames/job objects for this application
    """

    def __init__(self, app_repo, name):
        self.app_repo = app_repo
        self.name = name
        self.path = os.path.join(app_repo.path, name)
        self.versions = find_versions(os.path.join(self.path, 'modules'))
        self.doc = Documentation(self)
        self.jobs = find_jobs(os.path.join(self.path, 'jobs'))


# documentation class:
class Documentation(object):
    """Class to encapsulate all the information in regards to
    documentation for an application.

    Created by parsing the 'doc' subdirectory of an application within
    an application repository structure.
    """

    def __init__(self, application):
        self.application = application
        self.properties = {}
        self.tags = []
        self.versions = dict(application.versions)
        self.mdfiles = []
        self.app_doc_dir = os.path.join(application.path, 'doc')
        self.app_properties_file = os.path.join(self.app_doc_dir, 'app.properties')

        if os.path.isfile(self.app_properties_file):
            Config = ConfigParser.SafeConfigParser()
            Config.readfp(FakeSecHead(open(self.app_properties_file)))
            for key, value in Config.items('nosection'):
                if key == 'versions':
                    self.versions['N/A'] = [str(value).strip() for value in value.split(',')]
                elif key == 'tags':
                    self.tags = [str(value).strip() for value in value.split(',')]
                else:
                    self.properties[key] = value

        if os.path.isdir(self.app_doc_dir):
            md_files = [f for f in os.listdir(self.app_doc_dir) if f.endswith('.md') and os.path.getsize(os.path.join(self.app_doc_dir, f)) > 0]

            for f in md_files:
                self.mdfiles.append(f)


    def create_doc_page(self, template):
        """Generates documentation for an app, using the specified
        (velocity) template."""

        if type(template) is str:
            template = open(template, 'r')

        tmp_dir = '/tmp/app-org/' + self.application.name
        shutil.rmtree(tmp_dir, True)
        os.makedirs(tmp_dir)
        shutil.copy2(template.name, tmp_dir)
        loader = airspeed.CachingFileLoader(tmp_dir, True)

        for jobid in self.application.jobs:
            job_descriptions = self.application.jobs[jobid].job_descriptions
            job_md_files = self.application.jobs[jobid].mdfiles
            os.makedirs(os.path.join(tmp_dir, jobid))
            for job_desc in job_descriptions:
                shutil.copy2(os.path.join(self.application.jobs[jobid].path, job_desc), os.path.join(tmp_dir, jobid))

            for md_file in job_md_files:
                shutil.copy2(os.path.join(self.application.jobs[jobid].path, md_file), os.path.join(tmp_dir, jobid))

        for file in self.mdfiles:
            shutil.copy2(os.path.join(self.app_doc_dir, file), tmp_dir)

        template = loader.load_template(os.path.basename(template.name))

        # self.properties contains mainly the properties from the app.properties file
        properties = dict(self.properties)

        # helper functions
        properties['len'] = len
        properties['get_desc_id'] = get_desc_id
        properties['contains'] = list_contains
        properties['has_tag'] = has_tag

        properties['md_files'] = self.mdfiles
        properties['jobs'] = self.application.jobs
        properties['application'] = self.application
        properties['versions'] = self.versions
        properties['tags'] = self.tags

        result = template.merge(properties, loader=loader)
        return result

    def has_tag(self, tag):

        return has_tag(self.application.tags, tag)

# --------------------------------------------------------------------------------------
# Click cli stuff

pass_apprepo = click.make_pass_decorator(AppRepo)


@click.group()
@click.option('-a', '--app-repo',
              type=click.Path(exists=True, dir_okay=True),
              help='the path to the applications repository')
@click.pass_context
def cli(ctx, app_repo):
    if app_repo:
        ctx.obj = AppRepo(os.path.abspath(app_repo))

@cli.command(name='create-summary', short_help='renders a summary page using a template')
@click.option('--template', required=True,
              type=click.File(mode='r'),
              help='the template to create the summary page')
@click.option('--output-file', help='file to write summary page to')
@pass_apprepo
def create_summary(apprepo, template, output_file):
    """Generates a summary page with links to application sub-pages"""

    result = apprepo.create_summary_page(template)
    if not output_file:
        click.echo(result)
    else:
        with open(output_file, 'w') as text_file:
            text_file.write(result)


@cli.command(name='create-all', short_help='renders summaries as well as application specific documentation in one go, all templates used must be in the same directory')
@click.option('--template-dir',
              type=click.Path(exists=True, dir_okay=True),
              help='the path to where the templates are stored')
@click.option('--templates', help='comma-seperated list of templates to process, of not specified all files with an .md.vm extension will be used')
@click.option('--app-template', help='the template to use to create application pages, default: "app.md.vm"', default="app.md.vm")
@click.option('--output-dir', help='the directory to write the documentation into, application pages will be written in a subdirectory called "apps"', required=True)
@pass_apprepo
def create_all(apprepo, templates, template_dir, app_template, output_dir):

    if templates:
        templates = templates.split(",")
    else:
        templates = [f for f in os.listdir(template_dir) if f.endswith('.md.vm')]

    if app_template in templates:
        templates.remove(app_template)


    template = open(os.path.join(template_dir, app_template), 'r')
    create_app_documentation(apprepo, apprepo.apps.keys(), template, os.path.join(output_dir, "apps"))

    for t in templates:

        result = apprepo.create_summary_page(os.path.join(template_dir, t))
        output_file = os.path.join(output_dir, os.path.splitext(t)[0])
        with open(output_file, 'w') as text_file:
            text_file.write(result)




@cli.command(name='create-doc', short_help='renders application-specific documentation using a template')
@click.option('--template', required=True,
              type=click.File(mode='r'),
              help='the template to create the application page')
@click.option('--app', help='comma-seperated list of apps to create documentation for')
@click.option('--output-dir', help='directory to write documentation to')
@pass_apprepo
def create_doc(apprepo, template, app, output_dir):
    """Generates documentation for one or all applicatiions"""

    if app:
        apps = app.split(',')
        valid, msg = apprepo.check_valid_apps(apps)
        if not valid:
            click.echo(msg)
            sys.exit(1)
    else:
        apps = apprepo.apps.keys()


    create_app_documentation(apprepo, apps, template, output_dir)



if __name__ == '__main__':
    cli()
