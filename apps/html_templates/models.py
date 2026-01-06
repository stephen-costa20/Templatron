import uuid
from django.db import models

class Component(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    section = models.CharField(max_length=200, blank=True)
    tags = models.CharField(max_length=500, blank=True)  # comma-separated
    date_added = models.DateField(auto_now_add=True)
    code = models.TextField()
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started', blank=True)

    class Meta:
        ordering = ['-date_added', 'name']

    def tag_list(self):
        return [t.strip() for t in (self.tags or '').split(',') if t.strip()]

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'section': self.section,
            'tags': self.tag_list(),
            'dateISO': self.date_added.isoformat(),
            'code': self.code,
            'description': self.description,
            'notes': self.notes,
            'instructions': self.instructions,
            'status': self.status,
        }

class ComponentFile(models.Model):
    component = models.ForeignKey(Component, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='component_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.file.name.split('/')[-1],
            'url': self.file.url if self.file else '',
            'size': self.file.size if self.file else 0,
        }
