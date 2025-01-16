from django.db import models
from django.contrib.auth.models import User

class Login(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # User is linked via ForeignKey
    images = models.ImageField(upload_to='user_image')  # Uploaded images stored in 'user_image/' within MEDIA_ROOT

