from django.conf import settings

from league.models import League
from registration.models import RegistrationEvent


def league_processor(request):
    league = None

    # Override the theme for registration forms. Sometimes a user has a different
    # league set after login compared to the one attached to a registration event.
    try:
        if 'register' in request.resolver_match.namespaces:
            search_kwargs = {
                'league__slug': request.resolver_match.kwargs.get('league_slug', None),
                'slug': request.resolver_match.kwargs.get('event_slug', None),
            }
            league = RegistrationEvent.objects.get(**search_kwargs).league
    except AttributeError:
        pass
    except RegistrationEvent.DoesNotExist:
        pass

    if not league:
        league_id = request.session.get('view_league', None)
        if league_id:
            try:
                league = League.objects.get(pk=league_id)
            except League.DoesNotExist:
                pass

    return {'league_template': league, }


def debug(context):
    return {'DEBUG': settings.DEBUG}


def url_domain(request):
    return {'url_domain': settings.URL_DOMAIN}
