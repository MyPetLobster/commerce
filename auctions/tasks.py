import logging
import os
import smtplib

from celery import shared_task
from django.conf import settings
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Bid, Listing, Winner, User, Watchlist


logger = logging.getLogger(__name__)
my_email = os.environ.get('MY_EMAIL') 

@shared_task
def check_listing_expiration():
    try:
        now = timezone.now()

        # Filter active listings that are more than 7 days old
        expired_listings = Listing.objects.filter(active=True, date__lt=now - timezone.timedelta(days=7))

        for listing in expired_listings:
            # Close the listing
            listing.active = False
            listing.save()

            # Check for bids on the listing
            bids = Bid.objects.filter(listing=listing)
            if bids.exists():
                # Determine the highest bid
                highest_bid = bids.order_by('-amount').first()

                # Create a Winner object and save it to the database
                winner = Winner.objects.create(
                    amount=highest_bid.amount,
                    listing=listing,
                    user=highest_bid.user
                )

                # Notify the winner (implement this)
                notify_winner(winner, listing)
            else: 
                pass
    except (DatabaseError, IntegrityError, ObjectDoesNotExist) as e:
        logger.error(f"An error occurred while checking listing expiration: {str(e)}")
        send_error_notification(str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred while checking listing expiration: {str(e)}")
        send_error_notification(str(e))


def notify_winner(winner, listing):
    try:
        # Get the winner's email
        winner_email = winner.user.email

        # Create the email subject
        subject = f"Congratulations! You won an auction. ({winner_email})"

        listing_price = listing.price
        listing_title = listing.title
        seller_name = listing.user.username
        seller_email = listing.user.email

        # Create the email message
        message = render_to_string('auctions/winner_email.html', {
            'listing_title': listing_title,
            'listing_price': listing_price,
            'seller_name': seller_name,
            'seller_email': seller_email
        })
        
        #TODO currently using MY_EMAIL as the recipient for testing, change to winner_email
        # Send the email
        send_mail(
            subject,
            strip_tags(message),
            settings.EMAIL_HOST_USER,
            my_email,
            html_message=message
        )
    except (smtplib.SMTPException, smtplib.SMTPAuthenticationError, TemplateDoesNotExist) as e:
        logger.error(f"An error occurred while notifying the winner: {str(e)}")
        send_error_notification(str(e))


def send_error_notification(error_message):
    try:
        # Log the error
        logger.error(f'''------------------\n
                     An error occurred in the check_listing_expiration task: {error_message}\n
                     ------------------''')
        # Send error notification email to administrator
        send_mail(
            'Error Notification: Check Listing Expiration',
            f'An error occurred in the check_listing_expiration task: {error_message}',
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=False,
        )

    except (smtplib.SMTPException, smtplib.SMTPAuthenticationError) as e:
        logger.error(f"An error occurred while sending error notification: {str(e)}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending error notification: {str(e)}")











# @shared_task
# def check_listing_expiration():
#     listings = Listing.objects.filter(active=True)
#     for listing in listings:
#         if (datetime.now() - listing.date).days > 3:

#             # Close the listing
#             listing.active = False
#             listing.save()

#              # Check for winner if there are bids
#             bids = Bid.objects.filter(listing=listing)
#             if bids:
#                 highest_bid = bids.order_by('-amount').first()
#                 winner = Winner.objects.create(
#                     amount=listing.price,
#                     listing=listing,
#                     user=highest_bid.user
#                 )
#                 winner.save()

#                 # Email/Notify winner function here
#             else:
#                 pass
#         else:
#             pass