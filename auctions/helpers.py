from django.contrib import messages as contrib_messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone

import decimal
import logging
import math
from datetime import timedelta

from . import auto_messages as a_msg 
from .classes import UserBidInfo
from .models import Bid, Listing, Watchlist, User, Message, Transaction
from .tasks import send_message, transfer_to_escrow



logger = logging.getLogger(__name__)



# TODO Maybe move these to tasks.py

# Used in - views.index, views.listings
def set_inactive():
    listings = Listing.objects.filter(active=True)
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




# General Utility Helper Functions 
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


# Used Locally Only. Helpers for Helper Functions
def check_if_watchlist(user, listing):
    watchlist_item = Watchlist.objects.filter(user=user, listing=listing)
    if watchlist_item.exists():
        return True
    else:
        return False
    

def format_as_currency(amount):
    return f"${amount:,.2f}"



# HELPER FUNCTIONS - VIEWS.PY
# Used in views.listing, this chain of functions gets time left, and closes auctions if expired
def calculate_time_left(listing_id):
    '''
    This function calculates the time left on a listing and returns a string
    that in a format that is expected by my JavaScript countdown timer, which
    looks for a string in the format "days, hours, minutes, seconds" or a string
    that begins with "Listing" to determine what to display.

    Args: listing_id
    Returns: string

    Called by: views.listing
    Function Calls: check_expiration()
    '''

    closing_date = Listing.objects.get(pk=listing_id).closing_date
    current_date_time = timezone.now()
    seconds_left = (closing_date - current_date_time).total_seconds()

    if check_expiration(listing_id) == "closed - expired":
        return f"Listing expired on {closing_date.month}/{closing_date.day}/{closing_date.year}"
    elif check_expiration(listing_id) == "closed - by seller":
        return "Listing closed by seller"
    else:
        days_left, seconds_left = divmod(seconds_left, 86400)
        hours_left, remainder = divmod(seconds_left, 3600)
        minutes_left, seconds_left = divmod(remainder, 60)
        seconds_left = math.floor(seconds_left)
        return f"{int(days_left)} days, {int(hours_left)} hours, {int(minutes_left)} minutes, {int(seconds_left)} seconds"
    

def check_expiration(listing_id):
    '''
    This function checks if a listing is expired or closed by the seller. If the 
    listing is expired, it sets the listing to inactive and calls the declare_winner() 
    function to determine the winner if not yet set. Checks if the closing date is
    set to the default 7 days after the listing date, and if so, returns "closed - expired",
    otherwise, returns "closed - by seller".

    Args: listing_id
    Returns: string (used in calculate_time_left() function)

    Called by: calculate_time_left()
    Function Calls: declare_winner()
    '''

    listing = get_object_or_404(Listing, pk=listing_id)
    if listing.active:
        now = timezone.now()
        if listing.closing_date < now:
            listing.active = False
            listing.save()
            if listing.winner == None:
                declare_winner(listing)
                
            return "closed - expired"
        else:
            return "active"
    else:
        if listing.closing_date == listing.date + timedelta(days=7):
            return "closed - expired"
        else:
            return "closed - by seller"
        

def declare_winner(listing):
    '''
    Called when a listing is closed and no winner has been set. This function 
    sets the winner of the listing to the user with the highest bid. It then
    calls the transfer_to_escrow() function to transfer the winning bid amount
    from the winner's account to the escrow account. Finally, it calls the
    notify_all_closed_listing() function to notify all users that the listing
    has closed.

    Args: listing
    Returns: None

    Called by: check_expiration()
    Function Calls: transfer_to_escrow(), notify_all_closed_listing()
    '''
    if listing.winner:
        return
    
    highest_bid = Bid.objects.filter(listing=listing).order_by("-amount").first()
    if highest_bid:
        winner = highest_bid.user
        listing.winner = winner
        listing.save()
        
        transfer_to_escrow(winner, listing.id)
        a_msg.notify_all_closed_listing(listing.id)
        
        

# Place Bid Flow
@login_required
def check_valid_bid(request, listing_id, amount):
    '''
    Users are only permitted to place bids within 24 hours of the listing's closing date 
    if they have sufficient funds to cover the bid. This function checks these conditions,
    then calls the place_bid function if the conditions are met.

    Args: request, listing_id, amount
    Returns: None

    Called by: views.listing
    Function Calls: place_bid(), send_insufficient_funds_notification()
    '''

    current_user = request.user
    listing = Listing.objects.get(pk=listing_id)

    # Check if less than 24 hours left on the listing
    if listing.closing_date - timezone.now() < timedelta(days=1):
        # Check if user has enough funds to cover the bid
        if current_user.balance < amount:
            a_msg.send_insufficient_funds_notification(request, amount, listing.id)
        else:
            listing = place_bid(request, amount, listing.id)
    else:
        listing = place_bid(request, amount, listing.id)      
    return listing 


@login_required
def place_bid(request, amount, listing_id):
    '''
    This function creates a new bid object and saves it to the database. It then calls
    the check_bids_funds() function to handle the bid and send messages to the bidder and
    the previous high bidder if there was one. 
    
    Args: request, amount, listing_id
    returns: updated listing object

    Called by: check_valid_bid()
    Function Calls: check_bids_funds(), send_bid_success_message_seller(), message_previous_high_bidder(),
                    check_if_watchlist()
    '''
    try: 
        listing = Listing.objects.get(pk=listing_id)
        current_price = listing.price
        current_user = request.user

        # Redundant check. Should not ever be true, Django form should catch this
        if amount <= current_price:
            return listing

        # Get the previous high bidder and their bid amount to save in case the new bid is successful
        try: 
            previous_high_bidder = listing.bids.order_by("-amount").first().user
        except: 
            previous_high_bidder = None
        previous_high_bid = listing.price

        # Create the new bid object
        Bid.objects.create(
            amount=amount,
            listing=listing,
            user=current_user
        )

        # check_bids_funds() handles all bid situations and messages. 
        status, listing = check_bids_funds(request, listing_id)
        if status == True:
            # Send message to *seller* to notify of successful bid, other msgs handing in check_bids_funds()
            a_msg.send_bid_success_message_seller(request, amount, listing_id)
            # Message the previous high bidder if there was one
            if previous_high_bidder and previous_high_bidder != current_user:
                a_msg.message_previous_high_bidder(request, listing_id, previous_high_bidder, previous_high_bid)

        # Should never execute this block unless database error. Status will only be false if no bids exist
        # or if bid slipped through check_valid_bid()'s <24hr & <bid amount check
        elif status == False:
            logger.error(f"(Err01989)Unexpected error placing bid - bidder {current_user.name} - listing ID {listing.id} - amount {format_as_currency(amount)}")
            contrib_messages.add_message(request, contrib_messages.ERROR, f"Unexpected error placing bid. Please try again. If this issue persists, contact the admins.")
            return listing

        # Automatically add the item to the user's watchlist 
        if check_if_watchlist(current_user, listing) == False:
            Watchlist.objects.create(
                user=current_user,
                listing=listing
            )
        
        return listing

    except (Listing.DoesNotExist, ValueError, IntegrityError) as e:
        logger.error(f"(Err22222) Unexpected Error placing bid: {e}")
        return listing


@login_required
def check_bids_funds(request, listing_id):
    '''
    This function checks if a bid is valid and user has sufficient funds to cover the bid.
    If the bid is fully funded, success msg is sent. If bid is not fully funded, but over 
    24 hours remain on auction, success msg is sent including time left to deposit (until 
    24 hours before auction closes). If bid is not fully funded and less than 24 hours remain
    on auction, bid is cancelled and user is notified with an error message from place_bid().

    Args: request, listing_id
    returns: status, listing

    Called by: place_bid()
    Function Calls: send_bid_success_message_bidder(), send_bid_success_message_low_funds(),
                    send_bid_success_message_seller(), message_previous_high_bidder()
    '''
    listing = Listing.objects.get(pk=listing_id)
    now = timezone.now()
    bids = Bid.objects.filter(listing=listing)

    if bids.exists():
        highest_bid = bids.order_by('-amount').first()

        # Handle cases where the highest bid is greater than the user's balance.
        # Must have enough funds to cover bid deposited by the time the listing is 24 hours from closing
        if highest_bid.amount > highest_bid.user.balance:

            # Redundant check. Should not ever be true, checked already in check_valid_bid
            if listing.closing_date - timezone.timedelta(days=1) < now:
                highest_bid.delete()
                return False, listing

            # Send message to bidder to notify of insufficient funds and time left to deposit
            a_msg.send_bid_success_message_low_funds(request, highest_bid, listing.id)

        # If funds are sufficient, send success message to bidder     
        elif highest_bid.amount <= highest_bid.user.balance:
            a_msg.send_bid_success_message_bidder(request, highest_bid.amount, listing.id)

        # Update listing price to highest bid amount, save listing, and return True
        listing.price = highest_bid.amount
        listing.save()
        return True, listing

    # Bid should always exist, this is fail safe
    else:
        return False, listing








# Used in views.messages, actions.sort_messages
def set_message_sort(sort_by_direction, sent_messages, inbox_messages):
    '''
    This function sets the sort order for the user's sent and inbox messages. It is called
    by the views.messages view when the page is loaded, and called by the actions.sort_messages()
    function when the user clicks the "Sort" button. 

    Args: sort_by_direction - string,
                sent_messages - queryset of sent messages,
                inbox_messages - queryset of inbox messages
    Returns: sent_messages - queryset of sent messages,
                inbox_messages - queryset of inbox messages,
                sort_by_direction - string

    Called by: views.messages, actions.sort_messages
    '''
    
    if sort_by_direction == "oldest-first":
        sent_messages = sent_messages.order_by("date")
        inbox_messages = inbox_messages.order_by("date")
    else:
        sent_messages = sent_messages.order_by("-date")
        inbox_messages = inbox_messages.order_by("-date")

    return sent_messages, inbox_messages, sort_by_direction


def show_hide_read_messages(request):  
    '''
    This function toggles the display of read messages in the user's inbox. It is called
    by the views.messages view when the user clicks the "Show Read" button. It sets the
    show_read session variable to the opposite of its current value.

    Args: request
    Returns: sent_messages - queryset of sent messages,
                inbox_messages - queryset of inbox messages,
                show_read_messages - boolean,
                sort_by_direction - string

    Called by: views.messages
    '''
    current_user = request.user
    show_read_messages = request.session.get("show_read", False)

    if show_read_messages:
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
    if user_bids.exists():
        user_highest_bid = user_bids.order_by("-amount").first()
        if bid.amount < listing.price and bid.amount < user_highest_bid.amount:
            return True
        else:
            return False
    else:
        return False




# Used in views.listing

        
# views.profile
def create_bid_info_object_list(user_active_bids):
    '''
    Create a list of UserBidInfo objects to pass to the profile view. These objects
    provide additional information used in profile.html template. 

    Args: list of active bids for a user
    Returns: list of UserBidInfo objects

    Called by: views.profile
    '''
    bid_info_list = []

    for bid in user_active_bids:
        bid_listing = bid.listing
        is_old_bid = check_if_old_bid(bid, bid_listing)
        highest_bid = Bid.objects.filter(listing=bid_listing).order_by("-amount").first()
        highest_bid_amount = highest_bid.amount if highest_bid else 0
        difference = (bid.amount - highest_bid.amount) * -1 if highest_bid else 0

        user_bid_info = UserBidInfo(bid, is_old_bid, highest_bid_amount, difference)
        bid_info_list.append(user_bid_info)

    # sort the list by oldest listing to newest listing
    bid_info_list = sorted(bid_info_list, key=lambda x: x.user_bid.listing.date)




# ACTIONS.PY
    
def charge_early_closing_fee(listing_id):
    listing = Listing.objects.get(pk=listing_id)
    site_account = User.objects.get(pk=12)
    seller = listing.user
    fee_amount = round(listing.starting_bid * decimal.Decimal(0.05), 2)
 
    a_msg.send_early_closing_fee_message(listing_id, seller.id, fee_amount)

    Transaction.objects.create(
        sender=seller,
        recipient=site_account,
        amount=fee_amount,
        listing=listing
    )

