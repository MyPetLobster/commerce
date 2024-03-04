import logging
import os
import smtplib

from celery import shared_task
from django.conf import settings
from django.contrib import messages as contrib_messages
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Bid, Listing, Winner, User, Transaction, Message


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

                transfer_to_escrow(winner)
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
        # send_mail(
        #     'Error Notification: Check Listing Expiration',
        #     f'An error occurred in the check_listing_expiration task: {error_message}',
        #     settings.DEFAULT_FROM_EMAIL,
        #     [settings.ADMIN_EMAIL],
        #     fail_silently=False,
        # )

    except (smtplib.SMTPException, smtplib.SMTPAuthenticationError) as e:
        logger.error(f"An error occurred while sending error notification: {str(e)}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending error notification: {str(e)}")


def transfer_to_escrow(winner):
    listing = winner.listing
    buyer = winner.user
    amount = listing.price
    escrow_account = User.objects.get(pk=11)

    if amount > buyer.balance: 
        return False
        #TODO: add error message and email notification to buyer
    else:
        Transaction.objects.create(
            sender=buyer,
            recipient=escrow_account,
            amount=amount,
            listing=listing
        )

        buyer.balance -= amount
        buyer.save()
        escrow_account.balance += amount
        escrow_account.save()

        return True
    

def transfer_to_seller(listing_id):
    listing = Listing.objects.get(pk=listing_id)
    seller = listing.user
    amount = listing.price
    escrow_account = User.objects.get(pk=11)
    site_account = User.objects.get(pk=12)


    if amount > escrow_account.balance:
        #TODO: EMAIL ADMIN BALANCE ERROR BIG OOPS
        return False
    else:
        fee_amount = amount * 0.1
        amount -= fee_amount

        fee_transaction = Transaction.objects.create(
            sender=escrow_account,
            recipient=site_account,
            amount=fee_amount,
            listing=listing
        )
        fee_transaction.save()

        sell_transaction = Transaction.objects.create(
            sender=escrow_account,
            recipient=seller,
            amount=amount,
            listing=listing
        )
        sell_transaction.save()

        escrow_account.balance -= amount
        escrow_account.save()
        seller.balance += amount
        seller.save()
        return True
    

def send_message(sender, recipient, subject, message):
    Message.objects.create(
        sender=sender,
        recipient=recipient,
        subject=subject,
        message=message
    )
    

@shared_task
def check_bids_funds(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    now = timezone.now()
    bids = Bid.objects.filter(listing=listing)
    if bids.exists():
        highest_bid = bids.order_by('-amount').first()
        if highest_bid.amount > highest_bid.user.balance:
            if listing.date + timezone.timedelta(days=6) < now:
                send_message(
                    User.objects.get(pk=2),
                    highest_bid.user,
                    f"Insufficient funds for {listing.title}",
                    f"Your bid of {highest_bid.amount} on {listing.title} has been cancelled due to insufficient funds. Please add funds to your account to continue bidding."
                )
                highest_bid.delete()
                contrib_messages.add_message(request, contrib_messages.ERROR, f"Your bid of {highest_bid.amount} on {listing.title} has been cancelled due to insufficient funds. Please add funds to your account to continue bidding.")
                return False
            else:
                time_left_to_deposit = now - (listing.date + timezone.timedelta(days=6)) 
                time_left_to_deposit = f"{time_left_to_deposit.days} days, {time_left_to_deposit.seconds//3600} hours, {time_left_to_deposit.seconds%3600//60} minutes"
                send_message(
                    User.objects.get(pk=2),
                    highest_bid.user,
                    f"Insufficient funds for {listing.title}",
                    f"Your bid of {highest_bid.amount} on {listing.title}. You have {time_left_to_deposit} to add funds to your account before your bid for this listing is cancelled."
                )
                contrib_messages.add_message(request, contrib_messages.INFO, f"Your bid has been placed successfully, but you need to deposit funds. Check your messages for details.")
                return True
        elif highest_bid.amount <= highest_bid.user.balance:
            contrib_messages.add_message(request, contrib_messages.SUCCESS, f"Your bid of {highest_bid.amount} on {listing.title} has been placed successfully.")
            return True
    else:
        pass



