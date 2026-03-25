from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
User = get_user_model()

def _add_user_permissions(user):
    ct = ContentType.objects.get(app_label='auth', model='user')
    perms = Permission.objects.filter(content_type=ct, codename__in=('view_user', 'add_user', 'change_user', 'delete_user'))
    user.user_permissions.add(*perms)

class ProfileViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_profile_requires_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_ok_when_logged_in(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

class UserListViewTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='testpass123')
        _add_user_permissions(self.admin)
        self.other = User.objects.create_user(username='other', password='otherpass')

    def test_user_list_requires_login(self):
        response = self.client.get(reverse('accounts:list'))
        self.assertEqual(response.status_code, 302)

    def test_user_list_requires_permission(self):
        self.client.login(username='other', password='otherpass')
        response = self.client.get(reverse('accounts:list'))
        self.assertEqual(response.status_code, 403)

    def test_user_list_ok_with_permission(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('accounts:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin')
        self.assertContains(response, 'other')
