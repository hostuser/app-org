#! /usr/bin/python

import click
import airspeed
import shutil
import os
import ConfigParser
import collections


# helper functions
def list_length(list):
    return len(list)


# get basename of job_description
def get_desc_id(desc_name):
    return os.path.splitext(desc_name)[0]


# helper class needed to read sectionless property files
class FakeSecHead(object):
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

    versions = {}
    for root, dirs, files in os.walk(path):
        if len(files) > 0:
            cluster = os.path.basename(root).capitalize()
            versions[cluster] = sorted(files)

    return versions


class job:
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

    dirs = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    jobs = {}
    for directory in dirs:
        print directory
        j = job(os.path.join(path, directory))
        jobs[j.id] = j

    return collections.OrderedDict(sorted(jobs.items()))


# application class
class application:
    def __init__(self, app_repo, name):
        self.app_repo = app_repo
        self.name = name
        self.path = os.path.join(app_repo, name)
        self.versions = find_versions(os.path.join(self.path, 'modules'))
        self.doc = documentation(self)
        self.jobs = find_jobs(os.path.join(self.path, 'jobs'))


# documentation class:
class documentation:
    def __init__(self, application):
        self.application = application
        self.properties = {}
        self.properties['len'] = list_length
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


@click.command()
@click.option('-a', '--app-repo',
              type=click.Path(exists=True, dir_okay=True),
              help='the path to the applications repository')
@click.option('--template',
              type=click.File(mode='r'),
              help='the template to create the application page')
def create_doc(app_repo, template):
    """Generates documentation for one or all applicatiions"""

    create_doc_for_app(app_repo, 'R', template)


def create_doc_for_app(app_repo, app_name, template):

    tmp_dir = '/tmp/'+app_name
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


if __name__ == '__main__':
    create_doc()
