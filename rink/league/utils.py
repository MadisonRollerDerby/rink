from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string


def send_email(league, template, to_email, context={}):
    context['league'] = league
    context['url_domain'] = settings.URL_DOMAIN

    if league.email_from_name:
        from_email = "{} <{}>".format(league.email_from_name, league.email_from_address)
    else:
        from_email = league.email_from_address

    # the to_name field isn't working so hot right now for some mysterious reason.
    #if to_user:
    #    #to = "{} <{}>".format(to_user, to_user.email)
    #    to = "{}".format(to_user.email)
    #elif to_email and to_name:
    #    to = "{} <{}>".format(to_name, to_email)
    if to_email:
        to = "{}".format(to_email)
    else:
        raise ValueError("No user or email address passed, unable to send email.")

    # maybe these would be useful at some point?
    #context['from_email'] = from_email
    #context['to_email'] = name, etc? 

    # Get header HTML
    #if league.email_header:
    #    context['header_html'] = league.email_header
    #else:
    context['header_html'] = render_to_string('email/header_default.html', context)

    # Get footer HTML
    #if league.email_footer:
    #    context['footer_html'] = league.email_footer
    #else:
    context['footer_html'] = render_to_string('email/footer_default.html', context)

    subject = render_to_string('email/{}.subject'.format(template), context)
    message_html = render_to_string('email/{}.html'.format(template), context)
    try:
        message_txt = render_to_string('email/{}.txt'.format(template), context)
    except TemplateDoesNotExist:
        # By default we'll use BeautifulSoup for generating the text version
        # This kinda sucks, but otherwise we'll be creating raw text versions
        # of all the emails. Nobody really needs those anyway.... oh well.
        from bs4 import BeautifulSoup
        message_txt = BeautifulSoup(message_html, "html.parser").get_text("\n", strip=True)

    cc = None
    if league.email_cc_address:
        cc = [league.email_cc_address, ]

    msg = EmailMultiAlternatives(
        subject=subject,
        body=message_txt,
        from_email=from_email,
        to=[to_email, ],
        reply_to=[from_email, ],
        cc=cc,
    )
    msg.attach_alternative(message_html, "text/html")
    msg.send(fail_silently=False)

