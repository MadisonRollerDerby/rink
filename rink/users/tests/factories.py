import factory


# Simple user factory, no special privileges
class UserFactory(factory.django.DjangoModelFactory):
    email = factory.Sequence(lambda n: f'dev-{n}@madisonrollerderby.org')
    password = factory.PostGenerationMethodCall('set_password', 'password')

    class Meta:
        model = 'users.User'
        django_get_or_create = ('email', )



# Special factory for testing privileged users
class SuperUserFactory(factory.django.DjangoModelFactory):
    email = factory.Sequence(lambda n: f'dev-{n}@madisonrollerderby.org')
    password = factory.PostGenerationMethodCall('set_password', 'password')
    is_admin = True

    class Meta:
        model = 'users.User'
        django_get_or_create = ('email', )
