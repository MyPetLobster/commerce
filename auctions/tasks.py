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

                # Declare the winner
                winner = highest_bid.user
                listing.winner = winner
                listing.save()

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
    winner = listing.winner

    subject = f"Congratulations! You won the auction for {listing.title}"
    message = f"""If you have sufficient funds already deposited in your account, then you're all set and you should 
                have already received a message confirming funds have been moved to escrow. You will receive a message 
                with tracking information once the seller has shipped your item. If there is any further action 
                required on your part, you should have a message detailing the next steps. Thank you for using Yard Sale!"""
    send_message(site_account, winner, subject, message)

def message_seller_on_sale(listing_id):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    seller = listing.user

    subject = f"Congratulations! Your item has been sold!"
    message = f"""Your item, {listing.title}, has been sold! Please ship the item to the buyer as soon as possible.
                We make the process easy! A shipping label as been emailed to you. As soon as you ship the item, navigate back to
                the listing page via this link: <a href="/index/{listing.id}">{listing.id}</a> and click the 'Confirm Shipping' 
                button to confirm the sale. Once the item has been shipped, you will receive a message with tracking information. 
                Thank you for using Yard Sale!"""
    send_message(site_account, seller, subject, message)

def message_losing_bidders(listing_id):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    all_unique_bidders = Bid.objects.filter(listing=listing).values('user').distinct()

    winner = listing.winner
    all_unique_bidders = Bid.objects.filter(listing=listing).values('user').distinct()
    all_unique_bidders = all_unique_bidders.exclude(user=winner)

    for bidder in all_unique_bidders:
        user = User.objects.get(pk=bidder['user'])
        subject = f"Sorry, you lost the auction for {listing.title}"
        message = f"""Sorry, you lost the auction for {listing.title}. The winning bid was {winner.amount}. If there are 
                    and issues confirming the sale, the next highest bid will be contacted. Thank you for using Yard Sale!"""
        send_message(site_account, user, subject, message)


def notify_all_early_closing(listing_id):
    listing = Listing.objects.get(pk=listing_id)
    site_account = User.objects.get(pk=12)
    seller = listing.user
    all_unique_bidders = User.objects.filter(bids__listing=listing).distinct()

    if all_unique_bidders.exists():
        subject = f"A listing you been on is being closed early"
        message = f"""The listing for {listing.title} is being closed early by the seller. You have 
                    24 hours to continue bidding on this item. {listing.title} will be closed at 
                    {listing.closing_date}. Thank you for using Yard Sale!"""

        for bidder in all_unique_bidders:
            user = User.objects.get(pk=bidder['user'])
            send_message(site_account, user, subject, message)

        subject_seller = f"Your listing is being closed early"
        message_seller = f"""The listing for {listing.title} is being closed early. The new closing date is 
                            set for {listing.closing_date}. Because of the early cancellation, you will be 
                            charged an additional 5% fee when funds are transferred to you from escrow. 
                            If you did not close this listing, please contact support immediately. 
                            Thank you for using Yard Sale!"""
        
        send_message(site_account, seller, subject_seller, message_seller)


def charge_early_closing_fee(listing_id):

    listing = Listing.objects.get(pk=listing_id)
    site_account = User.objects.get(pk=12)
    seller = listing.user
    amount = listing.price
    fee_amount = amount * decimal.Decimal(0.05)


    Transaction.objects.create(
        sender=seller,
        recipient=site_account,
        amount=fee_amount,
        listing=listing
    )


def transfer_to_escrow(winner, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    buyer = winner.user
    amount = listing.price
    escrow_account = User.objects.get(pk=11)
    site_account = User.objects.get(pk=12)

    if amount > buyer.balance: 
        if listing.in_escrow == False:
            subject = f"Insufficient funds for {listing.title}"
            message = f"""You have won the bid for {listing.title}, but you do not have sufficient 
            funds to complete the transaction. Please add funds to your account to complete the purchase.
            Then navigate back to the listing page and click the 'Complete Purchase' button to complete 
            the transaction.
            """   
        else: 
            logger.error(f"(Err01989) Unexpected conflict with escrow status for {listing.title}")
        
    else:
        subject = f"Your funds have been deposited in escrow for {listing.title}"
        message = f"As soon as the buyer ships the item, you will receive confirmation and tracking information. Thank you for using Yard Sale!"

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
        listing.save()

    send_message(site_account, buyer, subject, message)
    

def transfer_to_seller(listing_id):
    listing = Listing.objects.get(pk=listing_id)
    seller = listing.user
    amount = listing.price
    buyer = listing.winner
    escrow_account = User.objects.get(pk=11)
    site_account = User.objects.get(pk=12)
    admin = User.objects.get(pk=2)

    if listing.in_escrow == True:
        if amount > escrow_account.balance:

            # Send Alert Message to Admin if escrow account is empty when it shouldn't be
            subject = "(Err 01989) Escrow Account Empty Alert - Listing: {listing.title}"
            message = f"""The escrow account is empty for {listing.title}. Please investigate and resolve this issue."""
            send_message(site_account, admin, subject, message)

            logger.error(f"(Err01989) Escrow account is empty for {listing.title}")
            return False
        else:

            #TODO Make sure to add cancellation charge when user lists item, and in terms

            # Check if the closing_date is less than 7 days after the listing date, signifying a cancellation
            if listing.closing_date < listing.date + timezone.timedelta(days=7):
                fee_amount = amount * decimal.Decimal(0.15)
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
                        Your balance should be updated within 1-2 business days. Here is the tracking 
                        number for your records #{tracking_number}. Thank you for using Yard Sale!
                        """
            send_message(site_account, seller, subject, message)


            # Send confirmation message to buyer after shipping confirmed
            subject = f"{listing.title} has been shipped!"
            message = f"""The funds held in escrow for {listing.title} have been released to the seller's account 
                        and your item has been shipped. Here is your tracking number: #{tracking_number}. 
                        Thank you for using Yard Sale!"""
            send_message(site_account, buyer, subject, message)

            return True
    else:
        logger.error(f"(Err01989) Unexpected conflict with escrow status for {listing.title}")
        return False
    

def send_message(sender, recipient, subject, message):
    Message.objects.create(
        sender=sender,
        recipient=recipient,
        subject=subject,
        message=message
    )




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