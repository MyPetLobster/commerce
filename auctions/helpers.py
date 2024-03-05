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
        
        transfer_to_escrow(winner)
        notify_all_closed_listing(listing.id)



# Used in - views.index, views.listings
def set_inactive(listings):
    for listing in listings:
        if listing.date + timedelta(days=7) < timezone.now():
            listing.active = False
            listing.closing_date = timezone.now()
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
        if listing.date + timedelta(days=7) < now:
            listing.active = False
            listing.closing_date = now
            listing.save()
            try:
                declare_winner(listing)
            except:
                pass
            return "closed - expired"
        else:
            return "active"
    else:
        if listing.date + timedelta(days=7) < timezone.now():
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
            bid = Bid.objects.create(
                amount=amount,
                listing=listing,
                user=current_user
            )
            
            admin = User.objects.get(pk=2)
            bidder = current_user
            subject = f"New bid on {listing.title}"
            message = f"You placed a bid of ${amount} on {listing.title}. Good luck!"
            send_message(admin, bidder, subject, message)

            if check_if_watchlist(current_user, listing) == False:
                Watchlist.objects.create(
                    user=current_user,
                    listing=listing
                )


            if check_bids_funds(request, listing_id) == True:
                listing.price = bid.amount
                listing.save()
                return True, listing
            else:
                return False, listing
        
    except (Listing.DoesNotExist, ValueError, IntegrityError) as e:
        logger.error(f"Error placing bid: {e}")
        return False


def check_bids_funds(request, listing_id):
    admin = User.objects.get(pk=2)
    listing = Listing.objects.get(pk=listing_id)
    now = timezone.now()
    bids = Bid.objects.filter(listing=listing)
    if bids.exists():
        highest_bid = bids.order_by('-amount').first()
        if highest_bid.amount > highest_bid.user.balance:
            if listing.date + timezone.timedelta(days=6) < now:
                send_message(
                    admin,
                    highest_bid.user,
                    f"Insufficient funds for {listing.title}",
                    f"Your bid of {highest_bid.amount} on {listing.title} has been cancelled due to insufficient funds. Please add funds to your account to continue bidding."
                )
                highest_bid.delete()
                contrib_messages.add_message(request, contrib_messages.ERROR, f"Your bid of {highest_bid.amount} on {listing.title} has been cancelled due to insufficient funds. Please add funds to your account to continue bidding.")
                return False
            else:
                time_left_to_deposit = listing.date + timezone.timedelta(days=6) - now
                time_left_to_deposit = f"{time_left_to_deposit.days} days, {time_left_to_deposit.seconds//3600} hours, {time_left_to_deposit.seconds%3600//60} minutes"
                highest_bid_amount = "${:0,.0f}".format(highest_bid.amount)
                send_message(
                    admin,
                    highest_bid.user,
                    f"Insufficient funds for '{listing.title}'",
                    f"Your bid of {highest_bid_amount} on '{listing.title}'. You have {time_left_to_deposit} to add funds to your account before your bid for this listing is cancelled."
                )
                contrib_messages.add_message(request, contrib_messages.INFO, f"Your bid has been placed successfully, but you need to deposit funds. Check your messages for details.")
                return True
        elif highest_bid.amount <= highest_bid.user.balance:
            contrib_messages.add_message(request, contrib_messages.SUCCESS, f"Your bid of {highest_bid.amount} on {listing.title} has been placed successfully.")
            return True
    else:
        pass



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