from django.urls import reverse, resolve


class URLTestCase(object):
    def check_url(self, name, path, reverse_args=[], reverse_kwargs={}):
        self.assertEqual(reverse(name, args=reverse_args, kwargs=reverse_kwargs), path)
        self.assertEqual(resolve(path).view_name, name)
