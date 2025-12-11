from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter

class NoSuccessMessageAdapter(DefaultSocialAccountAdapter, DefaultAccountAdapter):
    def add_message(self, request, level, message_template, message_context=None, extra_tags=''):
        # Disable ALL Allauth success messages
        return
