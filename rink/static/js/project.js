/* Project specific Javascript goes here. */

/*
Formatting hack to get around crispy-forms unfortunate hardcoding
in helpers.FormHelper:

    if template_pack == 'bootstrap4':
        grid_colum_matcher = re.compile('\w*col-(xs|sm|md|lg|xl)-\d+\w*')
        using_grid_layout = (grid_colum_matcher.match(self.label_class) or
                             grid_colum_matcher.match(self.field_class))
        if using_grid_layout:
            items['using_grid_layout'] = True

Issues with the above approach:

1. Fragile: Assumes Bootstrap 4's API doesn't change (it does)
2. Unforgiving: Doesn't allow for any variation in template design
3. Really Unforgiving: No way to override this behavior
4. Undocumented: No mention in the documentation, or it's too hard for me to find
*/
//$('.form-group').removeClass('row');


/*
AJAX crap for Registration Invite sending.
- Buttons require class of registration-invite-button.
- Clicking disables the button, changes text to 'Sending...' and fires AJAX call.
- AJAX call sends invite and returns with success.
- Successful call changes the button to 'Invite Sent' and disables the button.
*/
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});


$(document).ready(function() {
    $('.registration-invite-button').click(function() {
        var elem = this;
        if(!$(this).hasClass('disabled')) {
            $(this).addClass('disabled').html("Sending...");
            var req = $.post("/registration/test-event/invites", 
                { user_or_invite_id: $(this).attr("id") }
            ).done(function( data ) {
                jQuery(elem).html("Invite Sent");
                jQuery(elem).closest('tr').removeClass('table-warning table-info').addClass('table-info');
            });
        }
    });
});
