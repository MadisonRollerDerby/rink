from django.conf import settings

from league.models import League


def league_processor(request):
    league = None
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
