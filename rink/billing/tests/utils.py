from .factories import LeagueFactory, UserFactory


class BillingAppTestCase(object):
    def setUp(self):
        super().setUp()
        self.league = LeagueFactory()
        self.user = UserFactory(league=self.league, organization=self.league.organization)
        
    def tearDown(self):
        super().tearDown()
        if self.user:
            self.user.delete()
        if self.league:
            self.league.delete()
                
