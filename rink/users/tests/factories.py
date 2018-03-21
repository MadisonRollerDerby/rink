import factory


class UserFactory(factory.django.DjangoModelFactory):
    email = factory.Sequence(lambda n: f'dev-{n}@madisonrollerderby.org')
    password = factory.PostGenerationMethodCall('set_password', 'password')

    class Meta:
        model = 'users.User'
        django_get_or_create = ('email', )
