from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import encoding, six

from rest_framework.test import APITestCase as BaseAPITestCase
from rest_framework.utils.encoders import JSONEncoder

from webplatformcompat.history import Changeset


class TestMixin(object):
    """Useful methods for testing"""
    maxDiff = None
    baseUrl = 'http://testserver'

    def tearDown(self):
        cache.clear()

    def reverse(self, viewname, **kwargs):
        """Create a full URL for a view"""
        return self.baseUrl + reverse(viewname, kwargs=kwargs)

    def login_superuser(self):
        """Create and login a superuser, saving to self.user"""
        user = User.objects.create(
            username='staff', is_staff=True, is_superuser=True)
        user.set_password('5T@FF')
        user.save()
        self.assertTrue(self.client.login(username='staff', password='5T@FF'))
        self.user = user
        return user

    def create(self, klass, _history_user=None, _history_date=None, **kwargs):
        """Create a model, setting the historical relations"""
        obj = klass(**kwargs)
        obj._history_user = (
            _history_user or getattr(self, 'user', None) or
            self.login_superuser())

        if not hasattr(self, 'changeset'):
            hc_kwargs = {'user': obj._history_user}
            if _history_date is not None:
                hc_kwargs['created'] = _history_date
                hc_kwargs['modified'] = _history_date
            self.changeset = Changeset.objects.create(**hc_kwargs)
        obj._history_changeset = self.changeset

        if _history_date:
            obj._history_date = _history_date
        obj.save()
        return obj

    def normalizeData(self, data):
        """Attempt to recursively turn data into a normalized representation"""
        if isinstance(data, six.string_types):
            return encoding.smart_text(data)
        elif hasattr(data, 'items'):
            return dict([
                (self.normalizeData(key), self.normalizeData(value))
                for key, value in data.items()])
        elif isinstance(data, list):
            return [self.normalizeData(x) for x in data]
        else:
            return data

    def assertDataEqual(self, first, second):
        """Normalize two values to basic types before testing equality"""
        n_first = self.normalizeData(first)
        n_second = self.normalizeData(second)
        self.assertEqual(n_first, n_second)

    def dt_json(self, dt):
        """Convert a datetime to DRF encoded JSON"""
        return JSONEncoder().default(dt)

    def history_pk(self, obj):
        """Get the primary key of the current history instance."""
        return obj.history.all()[0].pk

    def history_pk_str(self, obj):
        """Get the primary key of the current history as a string."""
        return str(self.history_pk(obj))

    def history_pks(self, obj):
        """Get the primary keys of all the history instances."""
        return obj.history.all().values_list('pk', flat=True)

    def history_pks_str(self, obj):
        """Get the primary keys of all the history instances as strings."""
        return [str(pk) for pk in self.history_pks(obj)]


class TestCase(TestMixin, TestCase):
    """TestCase with useful methods"""
    pass


class APITestCase(TestMixin, BaseAPITestCase):
    """APITestCase with useful methods"""
    pass
