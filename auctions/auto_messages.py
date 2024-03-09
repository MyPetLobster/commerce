from django.contrib import messages as contrib_messages
from django.utils import timezone

from datetime import timedelta
import logging

from .models import Listing, User
from .tasks import send_message

logger = logging.getLogger(__name__)
site_account = User.objects.get(pk=12)

def format_as_currency(amount):
    return f"${amount:,.2f}"

def get_msg_info(request, listing_id):
    current_user = request.user
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    return current_user, site_account, listing




def send_insufficient_funds_notification(request, amount, listing_id):
    current_user, site_account, listing = get_msg_info(request, listing_id)
    subject = f"Insufficient funds for '{listing.title}' bid"
    message =f"""With less than 24 hours remaining on an auction, your account must have sufficient funds to cover any bids 
    on that auction. Your bid of {format_as_currency(amount)} on '{listing.title}' has been cancelled due to insufficient funds. Please 
    add funds to your account then try placing your bid again."""
    contrib_messages.add_message(request, contrib_messages.ERROR, f"""Insufficient funds. Less than 24 hours remain on this auction. 
                                 Bids must be covered by your account balance.""")
    send_message(site_account, current_user, subject, message)


def send_bid_success_message_seller(request, amount, listing_id):
    current_user, site_account, listing = get_msg_info(request, listing_id)
    subject = f"New bid on '{listing.title}'"
    message = f"{current_user.username} has placed a new {format_as_currency(amount)} bid on your listing, '{listing.title}'."
    send_message(site_account, listing.user, subject, message)
    logger.info(f"Success placing bid - bidder {current_user.username} - listing ID {listing.id} - amount {amount}")


def send_bid_success_message_bidder(request, amount, listing_id):
    current_user, site_account, listing = get_msg_info(request, listing_id)
    highest_bid_amount = format_as_currency(amount)
    subject = f"Success! You've placed a bid on {listing.title}"
    message = f"Your bid of {highest_bid_amount} on '{listing.title}' has been placed successfully. This item has been added to your watchlist. Good luck!"
    send_message(site_account, current_user, subject, message)
    contrib_messages.add_message(request, contrib_messages.SUCCESS, f"Your bid of {highest_bid_amount} on '{listing.title}' has been placed successfully.")



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


def message_previous_high_bidder(listing_id, previous_high_bidder, previous_high_bid):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    subject = f"Outbid on '{listing.title}'"
    message = f"You have been outbid on '{listing.title}'. The current bid is {format_as_currency(listing.price)}, which is {format_as_currency(listing.price - previous_high_bid)} more than your bid."
    send_message(site_account, previous_high_bidder, subject, message)
