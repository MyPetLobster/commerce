from django.conf import settings
from django.contrib import messages as contrib_messages
from django.core.mail import send_mail
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags


import logging
import os
import random
import smtplib

from .models import Listing, User, Bid, Message


my_email = os.environ.get('MY_EMAIL') 
logger = logging.getLogger(__name__)




# MESSAGE HELPER FUNCTIONS
def send_message(sender, recipient, subject, message):
    Message.objects.create(
        sender=sender,
        recipient=recipient,
        subject=subject,
        message=message
    )   

def format_as_currency(amount):
    return f"${amount:,.2f}"

def get_msg_info(request, listing_id):
    current_user = request.user
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    return current_user, site_account, listing

def check_for_mentions(comment):
    comment = comment.comment.split()
    mentions = []
    for word in comment:
        if word[0] == "@":
            if word[-1] == "," or word[-1] == ".":
                mentions.append(word[1:-1])
            mentions.append(word[1:])
    return mentions




# BID MESSAGES
# helpers.check_valid_bid()
def send_insufficient_funds_notification(request, amount, listing_id):
    current_user, site_account, listing = get_msg_info(request, listing_id)
    subject = f"Insufficient funds for '{listing.title}' bid"
    message =f"""With less than 24 hours remaining on an auction, your account must have sufficient funds to cover any bids 
    on that auction. Your bid of {format_as_currency(amount)} on '{listing.title}' has been cancelled due to insufficient funds. Please 
    add funds to your account then try placing your bid again."""
    contrib_messages.add_message(request, contrib_messages.ERROR, f"""Insufficient funds. Less than 24 hours remain on this auction. 
                                 Bids must be covered by your account balance.""")
    send_message(site_account, current_user, subject, message)

# helpers.place_bid()
def send_bid_success_message_seller(request, amount, listing_id):
    current_user, site_account, listing = get_msg_info(request, listing_id)
    subject = f"New bid on '{listing.title}'"
    message = f"{current_user.username} has placed a new {format_as_currency(amount)} bid on your listing, '{listing.title}'."
    send_message(site_account, listing.user, subject, message)
    logger.info(f"Success placing bid - bidder {current_user.username} - listing ID {listing.id} - amount {amount}")

# helpers.place_bid()
def message_previous_high_bidder(listing_id, previous_high_bidder, previous_high_bid):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    subject = f"Outbid on '{listing.title}'"
    message = f"You have been outbid on '{listing.title}'. The current bid is {format_as_currency(listing.price)}, which is {format_as_currency(listing.price - previous_high_bid)} more than your bid."
    send_message(site_account, previous_high_bidder, subject, message)

# helpers.check_bids_funds()
def send_bid_success_message_bidder(request, amount, listing_id):
    current_user, site_account, listing = get_msg_info(request, listing_id)
    highest_bid_amount = format_as_currency(amount)
    subject = f"Success! You've placed a bid on '{listing.title}'"
    message = f"Your bid of {highest_bid_amount} on '{listing.title}' has been placed successfully. This item has been added to your watchlist. Good luck!"
    send_message(site_account, current_user, subject, message)
    contrib_messages.add_message(request, contrib_messages.SUCCESS, f"Your bid of {highest_bid_amount} on '{listing.title}' has been placed successfully.")

# helpers.check_bids_funds()
def send_bid_success_message_low_funds(request, highest_bid, listing_id):
    now = timezone.now()
    current_user, site_account, listing = get_msg_info(request, listing_id)
    time_left_to_deposit = listing.closing_date - timezone.timedelta(days=1) - now
    if time_left_to_deposit.days == 0:
        time_left_to_deposit = f"{time_left_to_deposit.seconds//3600} hours, {time_left_to_deposit.seconds%3600//60} minutes"
    else:
        time_left_to_deposit = f"""{time_left_to_deposit.days} days, {time_left_to_deposit.seconds//3600} hours, 
        {time_left_to_deposit.seconds%3600//60} minutes"""
    highest_bid_amount = format_as_currency(highest_bid.amount)
    subject = f"Insufficient funds for '{listing.title}'"
    message = f"""Your bid of {highest_bid_amount} on '{listing.title}'. You have {time_left_to_deposit} to add funds to your account 
                before your bid for this listing is cancelled."""
    send_message(site_account, current_user, subject, message)
    contrib_messages.add_message(request, contrib_messages.INFO, f"""Your bid of {highest_bid_amount} has been placed successfully, 
                                 but you need to deposit funds. Check your messages for details.""")




# CLOSE LISTING MESSAGES
# helpers.declare_winner()
def notify_all_closed_listing(listing_id):
    message_winner(listing_id)
    message_seller_on_sale(listing_id)
    message_losing_bidders(listing_id)

## notify_all_closed_listing()
def message_winner(listing_id):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    winner = listing.winner

    subject = f"Congratulations! You won the auction for '{listing.title}'"
    message = f"""If you have sufficient funds already deposited in your account, then you're all set and you should 
                have already received a message confirming funds have been moved to escrow. You will receive a message 
                with tracking information once the seller has shipped your item. If there is any further action 
                required on your part, you should have a message detailing the next steps. Thank you for using Yard Sale!"""
    send_message(site_account, winner, subject, message)

## notify_all_closed_listing()
def message_seller_on_sale(listing_id):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    seller = listing.user

    subject = f"Congratulations! Your item has been sold!"
    message = f"""Your item, '{listing.title}', has been sold! Please ship the item to the buyer as soon as possible.
                We make the process easy! A shipping label as been emailed to you. As soon as you ship the item, navigate back to
                the listing page and click the 'Confirm Shipping' 
                button to confirm the sale. Once the item has been shipped, you will receive a message with tracking information. 
                Thank you for using Yard Sale!"""
    send_message(site_account, seller, subject, message)

## notify_all_closed_listing()
def message_losing_bidders(listing_id):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    winner = listing.winner
    all_unique_bidders = Bid.objects.filter(listing=listing).values('user').distinct()
    all_unique_bidders = all_unique_bidders.exclude(user=winner)

    for bidder in all_unique_bidders:
        user = User.objects.get(pk=bidder['user'])
        subject = f"Sorry, you lost the auction for '{listing.title}'"
        message = f"""Sorry, you lost the auction for '{listing.title}'. The winning bid was {format_as_currency(listing.price)} If there are 
                    and issues confirming the sale, the next highest bid will be contacted. Thank you for using Yard Sale!"""
        send_message(site_account, user, subject, message)


# helpers.declare_winner()
def notify_seller_closed_no_bids(listing_id):
    listing = Listing.objects.get(pk=listing_id)
    site_account = User.objects.get(pk=12)
    seller = listing.user
    subject = f"Your listing '{listing.title}' has been closed"
    message = f"""Your listing '{listing.title}' has been closed. Unfortunately, there were no bids on your item. 
                You may relist your item at any time. Thank you for using Yard Sale!"""
    send_message(site_account, seller, subject, message)


# actions.close_listing()
def notify_all_early_closing(listing_id):
    listing = Listing.objects.get(pk=listing_id)
    site_account = User.objects.get(pk=12)
    seller = listing.user
    all_unique_bidders = User.objects.filter(bids__listing=listing).distinct()

    new_closing_date = listing.closing_date
    new_closing_date = f'{new_closing_date.month}/{new_closing_date.day}/{new_closing_date.year}'

    if all_unique_bidders.exists():
        subject = f"An auction you been on is being closed early"
        message = f"""The listing for '{listing.title}' is being closed early by the seller. You have 
                    24 hours to continue bidding on this item. '{listing.title}' will be closed on 
                    {new_closing_date}. Because of the early closure, you will have 24 hours after the auction ends to
                    deposit sufficient funds. Thank you for using Yard Sale!"""

        for bidder in all_unique_bidders:
            user = User.objects.get(pk=bidder.id)
            send_message(site_account, user, subject, message)

        subject_seller = f"Your auction is being closed early"
        message_seller = f"""The auction for {listing.title} is being closed early. The new closing date is 
                            set for {new_closing_date}. Because of the early cancellation, you will be 
                            charged an additional 5% fee when funds are transferred to you from escrow. 
                            If you did not close this listing, please contact support immediately. 
                            Thank you for using Yard Sale!"""
        
        send_message(site_account, seller, subject_seller, message_seller)


# helpers.charge_early_closing_fee()
def send_fee_failure_message(listing, fee_amount):
    site_account = User.objects.get(pk=12)
    fee_amount_str = format_as_currency(fee_amount)
    seller = listing.user
    subject = f"Failed to charge early closing fee for '{listing.title}'"
    message = f"""The listing for '{listing.title}' was closed early. You have been charged a 5% fee in the amount of 
                {fee_amount_str}. We were unable to charge your account for this fee. Please deposit funds to cover this fee 
                within 7 business days to avoid additional fees. Thank you for your understanding and for using Yard Sale!"""
    send_message(site_account, seller, subject, message)


# tasks.check_user_fees()
def send_account_closure_message(user_id):
    site_account = User.objects.get(pk=12)
    user = User.objects.get(pk=user_id)
    subject = "Imminent account closure"
    message = f"""Your account has a negative balance and has been overdue for 28 days. If your account balance is not 
                brought to a positive value within 2 business days, your account will be closed and the negative balance 
                will be forwarded to our legal department. Please contact support immediately to resolve this issue."""
    send_message(site_account, user, subject, message)


# helpers.charge_early_closing_fee()
def send_early_closing_fee_message(listing, fee_amount):
    site_account = User.objects.get(pk=12)
    fee_amount_str = format_as_currency(fee_amount)
    subject = f"Early Closing Fee for '{listing.title}'"
    message = f"""The listing for {listing.title} was closed early. You have been charged a 5% fee in the amount of 
                {fee_amount_str}. This fee will be deducted from your balance directly.  
                Thank you for your understanding and for using Yard Sale! (and for the free $$$$)"""
    send_message(site_account, listing.user, subject, message)


# NOTIFY IF MENTIONED IN COMMENT
# actions.comment()
def notify_mentions(comment):
    listing_id = comment.listing.id
    listing = Listing.objects.get(pk=listing_id)
    site_account = User.objects.get(pk=12)
    mentions = check_for_mentions(comment)
    for mention in mentions:
        try:
            mention_user = User.objects.get(username=mention)
            subject = f"Someone's talking about you!"
            message = f"You've been mentioned by '{comment.user}' in a comment on '{listing.title}'."
            send_message(site_account, mention_user, subject, message)
        except User.DoesNotExist:
            pass


# CANCELLED BID MESSAGES - actions.cancel_bid() 
def send_bid_cancelled_message_confirmation(request, listing_id):
    current_user, site_account, listing = get_msg_info(request, listing_id)
    subject_cancelled_bid = "Cancelled Bid Successfully"
    message_cancelled_bid = f"Your bid on '{listing.title}' has been cancelled. This process automatically removes older bids on the same listing."
    send_message(site_account, current_user, subject_cancelled_bid, message_cancelled_bid)

def send_bid_cancelled_message_new_high_bidder(request, listing_id, highest_bid):
    current_user, site_account, listing = get_msg_info(request, listing_id)
    subject_new_high_bidder = f"Your bid on '{listing.title}' is now the highest bid."
    message_new_high_bidder = f"A user has cancelled their bid on '{listing.title}'. Your bid is now the highest bid. Good luck!"
    send_message(site_account, highest_bid.user, subject_new_high_bidder, message_new_high_bidder)

def get_bid_cancelled_message_seller_bids(request, listing_id, highest_bid):
    current_user, site_account, listing = get_msg_info(request, listing_id)  
    highest_bid_amount = format_as_currency(highest_bid.amount)
    subject_seller = f"A user has cancelled their bid on '{listing.title}'."
    message_seller = f"{current_user.username} has cancelled their bid on '{listing.title}'. The current high bid is now {highest_bid_amount}." 
    return subject_seller, message_seller

def get_bid_cancelled_message_seller_no_bids(request, listing_id):
    current_user, site_account, listing = get_msg_info(request, listing_id)
    subject_seller = f"A user has cancelled their bid on '{listing.title}'."
    message_seller = f"{current_user.username} has cancelled their bid on '{listing.title}'. There are no current bids."
    return subject_seller, message_seller


# WITHDRAW FUNDS MESSAGES - actions.withdraw()
def send_message_withdrawal_success(user_id, amount):
    site_account = User.objects.get(pk=12)
    user = User.objects.get(pk=user_id)
    subject = "Withdrawal Request Approved"
    message = f"Your withdrawal request for {format_as_currency(amount)} has been approved. Thank you for using Yard Sale!"
    send_message(site_account, user, subject, message)

def send_message_withdrawal_72(user_id, amount, total_funds_72, first_listing_to_close):
    site_account = User.objects.get(pk=12)
    user = User.objects.get(pk=user_id)
    subject = "Withdrawal Request Processed - Insufficient Funds for Bids"
    message = f"""Your withdrawal request for {format_as_currency(amount)} has been processed. However, this has left your account with 
                insufficient funds to cover active bids you've made on listings closing in less than 72 hours. As of the time of this message,
                your minimum balance needed to cover these bids is {format_as_currency(total_funds_72)} and your current balance is 
                {format_as_currency(user.balance)}. Our systems will automatically cancel and remove these bids if your balance is insufficient
                for each listing when it has 24 hours remaining. The listing that will expire first is '{first_listing_to_close.title}'. 
                We apologize for any inconvenience. Thank you for using Yard Sale!"""
    send_message(site_account, user, subject, message)

def send_message_deny_withdrawal(user_id, amount, total_funds_24):
    site_account = User.objects.get(pk=12)
    user = User.objects.get(pk=user_id)
    subject = "Withdrawal Request Denied"
    message = f"""Your withdrawal request for {format_as_currency(amount)} has been denied. You have active bids on listings closing
                in less than 24 hours and this withdrawal would leave your account balance below the amount needed to cover these bids. 
                As of the time of this message, your minimum balance needed to cover these bids is {format_as_currency(total_funds_24)}.
                We apologize for any inconvenience. Thank you for using Yard Sale!"""
    send_message(site_account, user, subject, message)


# ESCROW MESSAGES 
# helpers.transfer_to_escrow()
def get_escrow_fail_message(listing):
    subject = f"Insufficient funds for {listing.title}"
    message = f"""You have won the bid for {listing.title}, but you do not have sufficient 
    funds to complete the transaction. Please add funds to your account to complete the purchase.
    Then navigate back to the listing page and click the 'Complete Purchase' button to complete 
    the transaction. You have 24 hours from the closing time to complete the transaction before 
    your bid is cancelled and the next highest bidder is contacted. Thank you for using Yard Sale!"""   
    return subject, message

def get_escrow_success_message(listing):
    subject = f"Your funds have been deposited in escrow for {listing.title}"
    message = f"""As soon as the seller ships the item, you will receive confirmation and tracking information. 
    Thank you for using Yard Sale, and congratulations!"""
    return subject, message

# helpers.transfer_to_seller()
def send_escrow_empty_alert_message(listing_id):
    site_account = User.objects.get(pk=12)
    admin = User.objects.get(pk=2)
    listing = Listing.objects.get(pk=listing_id)
    subject = f"(Err 01989) Escrow Account Empty Alert - Listing: {listing.title}"
    message = f"""The escrow account is empty for {listing.title}. Please investigate and resolve this issue."""
    send_message(site_account, admin, subject, message)

def send_shipping_confirmation_messages(listing_id):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    seller = listing.user
    buyer = listing.winner
    tracking_number = random.randint(1000000000, 9999999999)

    subject_seller = f"Your tracking information has been received for {listing.title}"
    message_seller = f"""The funds held in escrow for {listing.title} have been released to your account. 
                Your balance should be updated within 1-2 business days. Here is the tracking 
                number for your records #{tracking_number}. Thank you for using Yard Sale!
                """
    subject_buyer = f"{listing.title} has been shipped!"
    message_buyer = f"""The funds held in escrow for {listing.title} have been released to the seller's account 
                and your item has been shipped. Here is your tracking number: #{tracking_number}. 
                Thank you for using Yard Sale!"""
    
    send_message(site_account, seller, subject_seller, message_seller)
    send_message(site_account, buyer, subject_buyer, message_buyer)


# REPORT MESSAGES
# actions.report_comment()
def send_comment_report_admin(current_user, comment, reason):
    site_account = User.objects.get(pk=12)
    admin = User.objects.get(pk=2)
    subject = f"{current_user.username} reported a comment"
    message = f"""{current_user.username} has reported a comment by {comment.user.username} on the listing '{comment.listing.title}' 
                for the following reason: {reason}. Here is the text of the comment: {comment.comment}"""
    send_message(site_account, admin, subject, message)

# actions.report_listing()
def send_listing_report_admin(current_user, listing, reason):
    site_account = User.objects.get(pk=12)
    admin = User.objects.get(pk=2)
    subject = f"{current_user.username} reported a listing"
    message = f"""{current_user.username} has reported the listing '{listing.title}' for the following reason: {reason}."""
    send_message(site_account, admin, subject, message)

# actions.report_user()
def send_user_report_admin(current_user, reported_user, reason):
    site_account = User.objects.get(pk=12)
    admin = User.objects.get(pk=2)
    subject = f"{current_user.username} reported a user"
    message = f"""{current_user.username} has reported the user {reported_user.username} for the following reason: {reason}."""
    send_message(site_account, admin, subject, message)



# PERIODIC TASKS MESSAGES
def send_bid_removed_message(user, listing, time_left_str):
    site_account = User.objects.get(pk=12)
    subject = f"Insufficient funds for {listing.title}"
    message = f"""As per the terms of the auction, your bid for '{listing.title}' has been cancelled and removed. 
                At the time of this message, there are {time_left_str} left in the auction. Feel free to deposit 
                funds and place another bid. We apologize for any inconvenience. Thank you for using Yard Sale!"""
    send_message(site_account, user, subject, message)




# EMAIL MESSAGES
def email_winner(winner, listing):
    try:
        # Get the winner's email
        winner_username = listing.winner.username

        # Create the email subject
        subject = f"Congratulations! You have the winning bid for '{listing.title}' (ID: {listing.id})"

        listing_price = listing.price
        listing_title = listing.title
        seller_name = listing.user.username
        seller_email = listing.user.email

        # Create the email message
        message = render_to_string('auctions/winner_email.html', {
            'admin_email': my_email,
            'winner_username': winner_username,
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
            [my_email,],
            html_message=message
        )
    except (smtplib.SMTPException, smtplib.SMTPAuthenticationError, TemplateDoesNotExist) as e:
        logger.error(f"An error occurred while notifying the winner: {str(e)}")
        send_error_msg_to_admin(str(e))


# Local Functions for this file
def send_error_msg_to_admin(error_message):
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


def message_admin_dispute(current_user, listing, reason):
    admin = User.objects.get(pk=2)
    subject = f"{current_user.username} has initiated a dispute for {listing.title}"
    message = f"{current_user.username} has initiated a dispute for {listing.title} for the following reason: {reason}."
    send_message(current_user, admin, subject, message)