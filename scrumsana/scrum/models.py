from asana import asana
from django.db import models
from django.conf import settings
from django.core.cache import cache

from .settings import ASANA_API_KEY

asana_api = asana.AsanaAPI(ASANA_API_KEY, debug=settings.DEBUG)


class Project(models.Model):
    """
    Asana project
    """
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255)

    cache_prefix = 'project'

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class Tag(models.Model):
    """
    Asana tags
    """
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255)

    cache_prefix = 'tag'

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class Assignee(models.Model):
    """
    Asana assignee
    """
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255)

    cache_prefix = 'assignee'

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class Workspace(models.Model):
    """
    Asana workspace
    http://developer.asana.com/documentation/#workspaces
    """
    id = models.BigIntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    is_organization = models.BooleanField(default=False)

    cache_prefix = 'workspace'

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class Task(models.Model):
    """
    Asana task
    http://developer.asana.com/documentation/#tasks
    """
    assignee = models.ForeignKey('Assignee', null=True)
    assignee_status = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField()
    due_on = models.DateTimeField(null=True)
    id = models.BigIntegerField(primary_key=True)
    modified_at = models.DateTimeField(null=True)
    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    parent = models.ForeignKey('self', null=True)
    projects = models.ManyToManyField('Project')
    tags = models.ManyToManyField('Tag')
    workspace = models.ForeignKey('Workspace', null=True)

    cache_prefix = 'task'

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name

    @classmethod
    def fetch_by_id(cls, id, force=False):
        """
        Fetches an Asana task by id using the Asana API. Will return the
        cached task unless force is True.
        """
        key = "{}_{}".format(cls.cache_prefix, id)
        task = cache.get(key)
        if force or not task:
            task = asana_api.get_task(id)
            cache.set(key, task)
        return cls.create_from_json(task)

    @classmethod
    def create_from_json(cls, task):
        """
        Creates a Task from the Asana API JSON response.
        """
        tags = []
        projects = []

        try:
            assignee_id = task['assignee']['id']
            assignee_name = task['assignee']['name']
            assignee, created = Assignee.objects.get_or_create(
                                    id=assignee_id, name=assignee_name)
        except TypeError:
            assignee = None

        try:
            workspace_id = task['workspace']['id']
            workspace_name = task['workspace']['name']
            workspace, created = Workspace.objects.get_or_create(
                                    id=workspace_id, name=workspace_name)
        except TypeError:
            workspace = None

        try:
            for t in task['tags']:
                tag, created = Tag.objects.get_or_create(
                                    id=t['id'], name=t['name'])
                tags.append(tag)
        except TypeError:
            pass

        try:
            for p in task['projects']:
                project, created = Project.objects.get_or_create(
                                        id=p['id'], name=p['name'])
                projects.append(project)
        except TypeError:
            pass

        task = cls(assignee=assignee,
                   assignee_status=task['assignee_status'],
                   completed=task['completed'],
                   completed_at=task['completed_at'],
                   created_at=task['created_at'],
                   due_on=task['due_on'],
                   id=task['id'],
                   modified_at=task['modified_at'],
                   name=task['name'],
                   notes=task['notes'],
                   parent=task['parent'],
                   workspace=workspace)

        task.save()

        task.tags = tags
        task.projects = projects

        task.save()

        return task
