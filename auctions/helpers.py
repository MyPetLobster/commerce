from django.contrib import messages as contrib_messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone

import logging
import math
from datetime import timedelta

from .models import Bid, Listing, Watchlist, User, Message
from .tasks import notify_all_closed_listing, send_message, transfer_to_escrow


logger = logging.getLogger(__name__)




# Used Locally Only
def check_if_watchlist(user, listing):
    watchlist_item = Watchlist.objects.filter(user=user, listing=listing)
    if watchlist_item.exists():
        return True
    else:
        return False
    

def declare_winner(listing):
    if listing.winner:
        return
    
    highest_bid = Bid.objects.filter(listing=listing).order_by("-amount").first()
    if highest_bid:
        winner = highest_bid.user
        listing.winner = winner
        
        transfer_to_escrow(winner, listing.id)
        notify_all_closed_listing(listing.id)


def format_as_currency(amount):
    return f"${amount:,.2f}"


# Used in - views.index, views.listings
def set_inactive(listings):
    for listing in listings:
        if listing.closing_date == None:
            listing.closing_date = listing.date + timedelta(days=7)
        if listing.closing_date < timezone.now():
            listing.active = False
            listing.save()
            try: 
                declare_winner(listing)
            except:
                pass
        else:
            pass




# Used in views.listing
def check_expiration(listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    if listing.active:
        now = timezone.now()
        if listing.closing_date < now:
            listing.active = False
            listing.save()
            try:
                declare_winner(listing)
            except:
                pass
            return "closed - expired"
        else:
            return "active"
    else:
        if listing.closing_date < timezone.now():
            return "closed - expired"
        else:
            return "closed - by seller"
        

def get_listing_values(request, listing):
    try:
        winner = User.objects.get(won_listings=listing)
    except User.DoesNotExist:
        winner = None
    try:
        user_bid = Bid.objects.filter(listing=listing, user=request.user).order_by("-amount").first()
    except:
        user_bid = None
    try:
        difference = listing.price - user_bid.amount
    except:
        difference = None
    try:
        watchlist_item = Watchlist.objects.filter(user=request.user, listing=listing)
    except:
        watchlist_item = None
    if watchlist_item.exists():
        pass
    else:
        watchlist_item = "not on watchlist"

    return winner, user_bid, difference, watchlist_item


def generate_time_left_string(difference_seconds):
    # Generate time left string to be handled in the template JS
    seconds_left = max(0, 604800 - difference_seconds)
    days_left, seconds_left = divmod(seconds_left, 86400)
    hours_left, remainder = divmod(seconds_left, 3600)
    minutes_left, seconds_left = divmod(remainder, 60)
    seconds_left = math.floor(seconds_left)
    time_left = f"{int(days_left)} days, {int(hours_left)} hours, {int(minutes_left)} minutes, {int(seconds_left)} seconds"

    return time_left




# Used in views.listing POST request
@login_required
def place_bid(request, amount, listing_id):
    try: 
        listing = Listing.objects.get(pk=listing_id)
        current_price = listing.price
        current_user = request.user

        if amount <= current_price:
            return False, listing
        else:
            Bid.objects.create(
                amount=amount,
                listing=listing,
                user=current_user
            )

            # This block will handle all bid situations and messages
            status, listing = check_bids_funds(request, listing_id)
            
            if status == True:
                logger.info(f"Success placing bid - bidder {current_user} - listing ID {listing.id} - amount {amount}")
            # Should never execute this block unless database error
            elif status == False:
                logger.error(f"(Err01989)Unexpected error placing bid - bidder {current_user} - listing ID {listing.id} - amount {amount}")
                contrib_messages.add_message(request, contrib_messages.ERROR, f"Unexpected error placing bid. Please try again. If this issue persists, contact the admins.")

            # Automatically add the item to the user's watchlist 
            if check_if_watchlist(current_user, listing) == False:
                Watchlist.objects.create(
                    user=current_user,
                    listing=listing
                )
            
            return True, listing

    except (Listing.DoesNotExist, ValueError, IntegrityError) as e:
        logger.error(f"(Err22222) Unexpected Error placing bid: {e}")
        return False, listing


def check_bids_funds(request, listing_id):
    site_account = User.objects.get(pk=12)
    listing = Listing.objects.get(pk=listing_id)
    now = timezone.now()
    bids = Bid.objects.filter(listing=listing)

    if bids.exists():

        highest_bid = bids.order_by('-amount').first()

        # Handle cases where the highest bid is greater than the user's balance.
        # Must have enough funds to cover bid deposited by the time the listing is 24 hours
        # from closing. There is a check in views.listing() to skip this if the listing is 
        # less than 24 hours from closing.
        if highest_bid.amount > highest_bid.user.balance:
            time_left_to_deposit = listing.closing_date - timezone.timedelta(days=1) - now
            if time_left_to_deposit.days == 0:
                time_left_to_deposit = f"{time_left_to_deposit.seconds//3600} hours, {time_left_to_deposit.seconds%3600//60} minutes"
            else:
                time_left_to_deposit = f"{time_left_to_deposit.days} days, {time_left_to_deposit.seconds//3600} hours, {time_left_to_deposit.seconds%3600//60} minutes"
            highest_bid_amount = format_as_currency(highest_bid.amount)
            subject = f"Insufficient funds for '{listing.title}'",
            message = f"Your bid of {highest_bid_amount} on '{listing.title}'. You have {time_left_to_deposit} to add funds to your account before your bid for this listing is cancelled."
            contrib_messages.add_message(request, contrib_messages.INFO, f"Your bid of {highest_bid_amount} has been placed successfully, but you need to deposit funds. Check your messages for details.")

        # If funds are sufficient, send success message      
        elif highest_bid.amount <= highest_bid.user.balance:
            highest_bid_amount = format_as_currency(highest_bid.amount)
            subject = f"Success! You've placed a bid on {listing.title}"
            message = f"Your bid of {highest_bid_amount} on {listing.title} has been placed successfully. This item has been added to your watchlist. Good luck!"
            contrib_messages.add_message(request, contrib_messages.SUCCESS, f"Your bid of {highest_bid_amount} on {listing.title} has been placed successfully.")
        
        # Update listing price to highest bid amount
        listing.price = highest_bid.amount
        listing.save()

        # Send message to bidder
        send_message(site_account, highest_bid.user, subject, message)

        return True, listing

    else:
        return False, listing



# Used in views.messages, actions.sort_messages
def determine_message_sort(request, sent_messages, inbox_messages):
    try:
        if request.session["sort_by_direction"] == None:
            sort_by_direction = "newest-first"
            request.session["sort_by_direction"] = sort_by_direction
        else:
            sort_by_direction = request.session["sort_by_direction"]
    except:
        sort_by_direction = "newest-first"
        request.session["sort_by_direction"] = sort_by_direction

    if sort_by_direction == "oldest-first":
        sent_messages = sent_messages.order_by("date")
        inbox_messages = inbox_messages.order_by("date")
    else:
        sent_messages = sent_messages.order_by("-date")
        inbox_messages = inbox_messages.order_by("-date")

    return sent_messages, inbox_messages, sort_by_direction


def show_hide_read_messages(request):  
    current_user = request.user
    try:
        if request.session["show_read"] == None:
            request.session["show_read"] = False
        
        if request.session["show_read"] == True:
            show_read_messages = "True"
        else:
            show_read_messages = "False"
    except:
        show_read_messages = "False"

    if show_read_messages == "True":
        sent_messages = Message.objects.filter(sender=current_user)
        inbox_messages = Message.objects.filter(recipient=current_user)
    else:
        sent_messages = Message.objects.filter(sender=current_user, read=False)
        inbox_messages = Message.objects.filter(recipient=current_user, read=False)

    sent_messages = sent_messages.exclude(deleted_by=current_user)
    inbox_messages = inbox_messages.exclude(deleted_by=current_user)

    return sent_messages, inbox_messages, show_read_messages




# Used in views.profile
def check_if_old_bid(bid, listing):
    user_bids = Bid.objects.filter(user=bid.user, listing=listing)
    if user_bids.count() > 1:
        if bid.amount < listing.price:
            return True
        else:
            return False