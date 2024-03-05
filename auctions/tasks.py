from celery import shared_task
from django.conf import settings
from django.db import DatabaseError, IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

import decimal
import logging
import os
import random
import smtplib

from .models import Bid, Listing, User, Transaction, Message


logger = logging.getLogger(__name__)
my_email = os.environ.get('MY_EMAIL') 



# Exclusively Celery Tasks
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
                notify_all_closed_listing(listing.id)
            else: 
                pass
    except (DatabaseError, IntegrityError, ObjectDoesNotExist) as e:
        logger.error(f"An error occurred while checking listing expiration: {str(e)}")
        send_error_notification(str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred while checking listing expiration: {str(e)}")
        send_error_notification(str(e))


def send_error_notification(error_message):
    try:
        site_account = User.objects.get(pk=12)
        admin = User.objects.get(pk=2)
        subject = "An error occurred in the Yard Sale application"
        message = error_message
        send_message(site_account, admin, subject, message)

    except (smtplib.SMTPException, smtplib.SMTPAuthenticationError) as e:
        logger.error(f"SMTP related error occurred while sending error notification: {str(e)}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending error notification: {str(e)}")




# Helper Functions for Celery Tasks (Also used in views/actions/helpers.py)
def notify_all_closed_listing(listing_id):
    message_winner(listing_id)
    message_seller_on_sale(listing_id)
    message_losing_bidders(listing_id)


def message_winner(listing_id):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    winner = Winner.objects.get(listing=listing)

    subject = f"Congratulations! You won the auction for {listing.title}"
    message = f"""If you have sufficient funds already deposited in your account, then you're all set! If there 
                is any further action required on your part, you will receive a message detailing the next steps.
                Otherwise, you will receive a message with tracking information once the seller has shipped your item. 
                Thank you for using Yard Sale!"""
    send_message(site_account, winner.user, subject, message)

def message_seller_on_sale(listing_id):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    seller = listing.user

    subject = f"Congratulations! Your item has been sold!"
    message = f"""Your item, {listing.title}, has been sold! Please ship the item to the buyer as soon as possible.
                We make the process easy! A shipping label as been emailed to you. As soon as you ship the item, navigate back to
                the listing page via this link: <a href="/index/{listing.id}">{listing.id}</a> and click the 'Confirm Shipping' button to confirm the sale.
                Once the item has been shipped, you will receive a message with tracking information. Thank you for using Yard Sale!"""
    send_message(site_account, seller, subject, message)

def message_losing_bidders(listing_id):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    all_unique_bidders = Bid.objects.filter(listing=listing).values('user').distinct()

    winner = Winner.objects.get(listing=listing)
    all_unique_bidders = all_unique_bidders.exclude(user=winner.user)

    for bidder in all_unique_bidders:
        user = User.objects.get(pk=bidder['user'])
        subject = f"Sorry, you lost the auction for {listing.title}"
        message = f"""Sorry, you lost the auction for {listing.title}. The winning bid was {winner.amount}. If there are 
                    and issues confirming the sale, the next highest bid will be contacted. Thank you for using Yard Sale!"""
        send_message(site_account, user, subject, message)

# def email_winner(winner, listing):
#     try:
#         # Get the winner's email
#         winner_email = winner.user.email

#         # Create the email subject
#         subject = f"Congratulations! You won an auction. ({winner_email})"

#         listing_price = listing.price
#         listing_title = listing.title
#         seller_name = listing.user.username
#         seller_email = listing.user.email

#         # Create the email message
#         message = render_to_string('auctions/winner_email.html', {
#             'listing_title': listing_title,
#             'listing_price': listing_price,
#             'seller_name': seller_name,
#             'seller_email': seller_email
#         })
        
#         #TODO currently using MY_EMAIL as the recipient for testing, change to winner_email
#         # Send the email
#         send_mail(
#             subject,
#             strip_tags(message),
#             settings.EMAIL_HOST_USER,
#             [my_email,],
#             html_message=message
#         )
#     except (smtplib.SMTPException, smtplib.SMTPAuthenticationError, TemplateDoesNotExist) as e:
#         logger.error(f"An error occurred while notifying the winner: {str(e)}")
#         send_error_notification(str(e))

def transfer_to_escrow(winner):
    listing = winner.listing
    buyer = winner.user

    amount = listing.price
    escrow_account = User.objects.get(pk=11)

    if amount > buyer.balance: 
        if listing.in_escrow == False:
            subject = f"Insufficient funds for {listing.title}"
            message = f"""You have won the bid for {listing.title}, but you do not have sufficient 
            funds to complete the transaction. Please add funds to your account to complete the purchase.
            Then navigate back to the listing page via this link: {listing.get_absolute_url()} and click 
            the 'Complete Purchase' button to complete the transaction.
            """
            send_message(User.objects.get(pk=2), buyer, subject, message)
        else: 
            logger.error(f"Unexpected conflict with escrow status for {listing.title}")
        
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
        listing.in_escrow = True
    

def transfer_to_seller(listing_id):
    listing = Listing.objects.get(pk=listing_id)
    seller = listing.user
    amount = listing.price
    buyer = Winner.objects.get(listing=listing).user
    escrow_account = User.objects.get(pk=11)
    site_account = User.objects.get(pk=12)
    admin = User.objects.get(pk=2)

    if listing.in_escrow == True:
        if amount > escrow_account.balance:
            # Send Alert Message to Admin if escrow account is empty when it shouldn't be
            subject = "Escrow Account Empty Alert - Listing: {listing.title}"
            message = f"""The escrow account is empty for {listing.title}. Please investigate and resolve this issue."""
            send_message(site_account, admin, subject, message)
            return False
        else:
            fee_amount = amount * decimal.Decimal(0.1)
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

            listing.in_escrow = False

            tracking_number = random.randint(1000000000, 9999999999)

            # Send confirmation message to seller after shipping confirmed
            subject = f"Your tracking information has been received for {listing.title}"
            message = f"""The funds held in escrow for {listing.title} have been released to your account. 
                        Your balance should be updated within 1-2 business days. Thank you for using Yard Sale!
                        """
            send_message(site_account, seller, subject, message)


            # Send confirmation message to buyer after shipping confirmed
            subject = f"{listing.title} has been shipped!"
            message = f"""The funds held in escrow for {listing.title} have been released to the seller's account 
                        and your item has been shipped. Here is your tracking number: {tracking_number}. 
                        Thank you for using Yard Sale!"""
            send_message(site_account, buyer, subject, message)

            return True
    else:
        logger.error(f"Unexpected conflict with escrow status for {listing.title}")
        return False
    

def send_message(sender, recipient, subject, message):
    Message.objects.create(
        sender=sender,
        recipient=recipient,
        subject=subject,
        message=message
    )

