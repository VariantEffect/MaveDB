import logging

from django import forms
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model

from core.tasks import email_user, send_to_email

User = get_user_model()
logger = logging.getLogger("django")


class ContactForm(forms.Form):
    """
    Contact form. Emails are send to administrators.
    """
    name = forms.CharField(
        label="Preferred contact name",
        required=True,
        max_length=64
    )
    email = forms.EmailField(
        label="Contact Email",
        required=True,
        help_text="The email address you would like to be contacted with.",
        max_length=64
    )
    subject = forms.CharField(
        label="Subject",
        required=True,
        max_length=128
    )
    message = forms.CharField(
        label="Message",
        help_text="Please leave your message below.",
        required=True,
        widget=forms.Textarea(attrs={'rows': 20})
    )
    
    def send_mail(self):
        if self.is_bound and self.is_valid():
            name = self.cleaned_data.get("name", "")
            subject = self.cleaned_data.get("subject", "")
            message = self.cleaned_data.get("message", "")
            email = self.cleaned_data.get("email", "")
            if email and message and subject and name:
                admins = User.objects.filter(is_superuser=True).all()
                for admin in admins:
                    logger.info("Sending contact email to {} from {}".format(
                        admin.username, email))
                    email_user.delay(
                        user=admin.pk,
                        subject='[MaveDB Help] ' + subject,
                        message=message,
                        from_email=email
                    )

                # Send confirmation response.
                template = 'main/message_received.html'
                fmt_message = render_to_string(template, {
                    'name': name,
                    'message': message,
                })
                send_to_email.delay(
                    subject="Your message has been recieved.",
                    message=fmt_message,
                    from_email="no-reply@mavedb.org",
                    recipient_list=[email],
                )
