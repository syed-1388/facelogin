from django.contrib import admin
from .models import Login

class LoginAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'images')  # Display username and images in the list

    def get_username(self, obj):
        return obj.user.username  # Accessing the 'username' field from the 'user' ForeignKey

    get_username.admin_order_field = 'user'  # Make it sortable by user
    get_username.short_description = 'Username'  # Column header for username

admin.site.register(Login, LoginAdmin)
