from django.contrib import messages as contrib_messages
from django.utils import timezone

from datetime import timedelta
import logging

from .models import Listing, User, Bid
from .tasks import send_message

logger = logging.getLogger(__name__)

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

    new_closing_date = listing.closing_date
    new_closing_date = f'{new_closing_date.month}/{new_closing_date.day}/{new_closing_date.year}'

    if all_unique_bidders.exists():
        subject = f"An auction you been on is being closed early"
        message = f"""The listing for {listing.title} is being closed early by the seller. You have 
                    24 hours to continue bidding on this item. {listing.title} will be closed on 
                    {new_closing_date}. Thank you for using Yard Sale!"""

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





def notify_mentions(comment):
    listing_id = comment.listing.id
    listing = Listing.objects.get(pk=listing_id)
    site_account = User.objects.get(pk=12)
    mentions = check_for_mentions(comment)
    for mention in mentions:
        try:
            mention_user = User.objects.get(username=mention)
            subject = f"Someone's talking about you!"
            message = f"You've been mentioned by {comment.user} in a comment on '{listing.title}'."
            send_message(site_account, mention_user, subject, message)
        except User.DoesNotExist:
            pass


def check_for_mentions(comment):
    comment = comment.comment.split()
    mentions = []
    for word in comment:
        if word[0] == "@":
            mentions.append(word[1:])
    return mentions


def send_early_closing_fee_message(listing, fee_amount):
    site_account = User.objects.get(pk=12)
    fee_amount_str = format_as_currency(fee_amount)
    subject = f"Early Closing Fee for '{listing.title}'"
    message = f"""The listing for {listing.title} was closed early. You have been charged a 5% fee in the amount of 
                {fee_amount_str}. This fee will be deducted from your balance directly. If this overdraws your account, you 
                have 7 business days to deposit funds to cover the fee, before additional fees begin to accrue. 
                Thank you for your understanding and for using Yard Sale! (and for the free $$$$)"""
    send_message(site_account, listing.seller, subject, message)