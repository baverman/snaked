from django.db import models

class Blog(models.Model):
    name = models.TextField()

class Post(models.Model):
    blog = models.ForeignKey(Blog, related_name='bposts')
    body = models.TextField()
    