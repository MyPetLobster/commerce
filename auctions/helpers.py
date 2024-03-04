import logging
import math
from datetime import timedelta, timezone

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Bid, Winner, Listing, Watchlist, User, Message

from .tasks import notify_winner, transfer_to_escrow, send_message, check_bids_funds

logger = logging.getLogger(__name__)


# helper for place_bid
def check_if_watchlist(user, listing):
    watchlist_item = Watchlist.objects.filter(user=user, listing=listing)
    if watchlist_item.exists():
        return True
    else:
        return False
    

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
            bid.save()
            
            admin = User.objects.get(pk=2)
            bidder = current_user
            subject = f"New bid on {listing.title}"
            message = f"You placed a bid of ${amount} on {listing.title}. Good luck!"
            send_message(admin, bidder, subject, message)

            if check_if_watchlist(current_user, listing) == False:
                watchlist_item = Watchlist.objects.create(
                    user=current_user,
                    listing=listing
                )
                watchlist_item.save()

            if check_bids_funds(request, listing_id) == True:
                listing.price = bid.amount
                listing.save()
                return True, listing
            else:
                return False, listing
        
    except (Listing.DoesNotExist, ValueError, IntegrityError) as e:
        logger.error(f"Error placing bid: {e}")
        return False

def declare_winner(listing):
    if Winner.objects.filter(listing=listing).exists():
        return
    
    highest_bid = Bid.objects.filter(listing=listing).order_by("-amount").first()
    if highest_bid:
        winner = Winner.objects.create(
            amount=listing.price,
            listing=listing,
            user=highest_bid.user
        )
        notify_winner(winner, listing)
        transfer_to_escrow(winner)


# Index, Listing, Listings Helper Functions
def set_inactive(listings):
    for listing in listings:
        if listing.date + timedelta(days=7) < timezone.now():
            listing.active = False
            listing.save()
            try: 
                declare_winner(listing)
            except:
                pass
        else:
            pass


def check_expiration(listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    if listing.active:
        now = timezone.now()
        if listing.date + timedelta(days=7) < now:
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
        if listing.date + timedelta(days=7) < timezone.now():
            return "closed - expired"
        else:
            return "closed - by seller"
        

def get_listing_values(request, listing):
    try:
        winner = Winner.objects.get(listing=listing)
    except Winner.DoesNotExist:
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


def check_if_old_bid(bid, listing):
    user_bids = Bid.objects.filter(user=bid.user, listing=listing)
    if user_bids.count() > 1:
        if bid.amount < listing.price:
            return True
        else:
            return False