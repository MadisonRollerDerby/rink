from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_aware, make_aware


def get_aware_datetime(date_str):
    # https://stackoverflow.com/a/24228410
    ret = parse_datetime(date_str)
    if not is_aware(ret):
        ret = make_aware(ret)
    return ret