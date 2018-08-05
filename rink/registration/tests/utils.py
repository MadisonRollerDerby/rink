from registration.tests.factories import RegistrationEventFactory


class RegistrationEventTest(object):
    def setUp(self):
        super().setUp()

        try:
            self.event
        except AttributeError:
            self.event = RegistrationEventFactory(league=self.league)
            self._url_kwargs = {'event_slug': self.event.slug}
