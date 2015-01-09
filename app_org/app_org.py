#! /usr/bin/python

import click
import airspeed
import shutil
import os
import ConfigParser
import collections

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


class AppRepo(object):

    def __init__(self, path):
        self.path = path


pass_apprepo = click.make_pass_decorator(AppRepo)


class job(object):
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
            if os.path.isfile(os.path.join(self.path, sl_id+".md")):
                self.job_descriptions[f] = sl_id + ".md"
            else:
                self.job_descriptions[f] = None

        for root, dirs, files in os.walk(self.job_files_path):
            for file in files:
                relative = root[len(self.job_files_path):]
                if relative:
                    self.job_files.append(relative[1:]+"/"+file)
                else:
                    self.job_files.append(file)

        self.job_files.sort()
        

def find_jobs(path):
    """Returns a sorted dictionary of jobname/job(object) for a
    specified path."""
    
    dirs = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    jobs = {}
    for directory in dirs:
        print directory
        j = job(os.path.join(path, directory))
        jobs[j.id] = j

    return collections.OrderedDict(sorted(jobs.items()))


# application class
class application(object):
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
        self.path = os.path.join(app_repo, name)
        self.versions = find_versions(os.path.join(self.path, 'modules'))
        self.doc = documentation(self)
        self.jobs = find_jobs(os.path.join(self.path, 'jobs'))


# documentation class:
class documentation(object):
    """Class to encapsulate all the information in regards to
    documentation for an application.

    Created by parsing the 'doc' subdirectory of an application within
    an application repository structure.
    """
    def __init__(self, application):
        self.application = application
        self.properties = {}
        self.properties['len'] = len
        self.properties['get_desc_id'] = get_desc_id
        self.tags = []
        self.versions = dict(application.versions)
        self.properties['versions'] = self.versions
        self.mdfiles = []
        self.app_doc_dir = os.path.join(application.path, 'doc')
        self.app_properties_file = os.path.join(self.app_doc_dir, 'app.properties')

        if os.path.isfile(self.app_properties_file):
            Config = ConfigParser.SafeConfigParser()
            Config.readfp(FakeSecHead(open(self.app_properties_file)))
            for key, value in Config.items('nosection'):
                if key == 'versions':
                    self.versions['N/A'] = [str(value).strip() for value in value.split(',')]
                if key == 'tags':
                    self.tags = [str(value).strip() for value in value.split(',')]
                    self.properties[key] = self.tags
                else:
                    self.properties[key] = value

        md_files = [f for f in os.listdir(self.app_doc_dir) if f.endswith('.md')]

        for f in md_files:
            self.properties[f] = f
            self.mdfiles.append(f)


@click.group()
@click.option('-a', '--app-repo',
              type=click.Path(exists=True, dir_okay=True),
              help='the path to the applications repository')
@click.pass_context
def cli(ctx, app_repo):
    ctx.obj = AppRepo(os.path.abspath(app_repo))


@cli.command()
@click.option('--template',
              type=click.File(mode='r'),
              help='the template to create the application page')
@pass_apprepo
def create_doc(apprepo, template):
    """Generates documentation for one or all applicatiions"""
    print type(apprepo)
    application_repo = apprepo.path
    create_doc_for_app(application_repo, 'R', template)


def create_doc_for_app(app_repo, app_name, template):
    """Generates documentation for an app, using the specified
    (velocity) template."""
    
    tmp_dir = '/tmp/app-org/'+app_name
    shutil.rmtree(tmp_dir, True)
    os.makedirs(tmp_dir)
    shutil.copy2(template, tmp_dir)
    loader = airspeed.CachingFileLoader(tmp_dir, True)
    app = application(app_repo, app_name)
    doc = documentation(app)

    for jobid in app.jobs:
        job_descriptions = app.jobs[jobid].job_descriptions
        job_md_files = app.jobs[jobid].mdfiles
        os.makedirs(os.path.join(tmp_dir, jobid))
        for job_desc in job_descriptions:
            shutil.copy2(os.path.join(app.jobs[jobid].path, job_desc), os.path.join(tmp_dir, jobid))

        for md_file in job_md_files:
            shutil.copy2(os.path.join(app.jobs[jobid].path, md_file), os.path.join(tmp_dir, jobid))
            
    for file in doc.mdfiles:
        shutil.copy2(os.path.join(doc.app_doc_dir, file), os.path.join(tmp_dir, jobid))

    template = loader.load_template(os.path.basename(template))

    properties = dict(doc.properties)
    properties['jobs'] = app.jobs
    properties['application'] = app

    result = template.merge(properties, loader=loader)
    print result


