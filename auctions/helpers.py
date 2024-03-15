from django.contrib import messages as contrib_messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone

import decimal
import logging
import math
import re
from datetime import timedelta

from .banned_words import banned_words_list
from . import auto_messages as a_msg 
from .classes import UserBidInfo
from .models import Bid, Listing, Watchlist, User, Message, Transaction




logger = logging.getLogger(__name__)




# GENERAL UTILITY HELPER FUNCTIONS

def format_as_currency(amount):
    return f"${amount:,.2f}"


def filter_profanity(text):
    '''
    This function filters out profanity from text. It is called by the actions.comment() function
    to filter out profanity from user comments.

    Args:
            text (str): the text to be filtered
    Returns:
            text (str): the filtered text, replacing profanity with asterisks

    Called by: actions.comment()
    Function Calls: None
    '''
    banned_words = banned_words_list() 
    words = re.findall(r'\b[\w\'\-]+\b|[.,!?;: ]', text)  # Split text into words and retain punctuation and whitespace
    censored_text = []

    for word in words:
        censored_word = word
        if word not in '.,!?;:':  # Skip punctuation marks and whitespace
            for banned_word in banned_words:
                if banned_word in word.lower():
                    censored_word = '*' * len(word)
                    break  # Stop checking once a banned word is found in the word
        censored_text.append(censored_word)

    return ''.join(censored_text)




# HELPER FUNCTIONS - ACTIONS.PY

# actions.close_listing()    
def charge_early_closing_fee(listing_id):
    '''
    This function charges the seller a 5% fee if they close the listing early. It is called
    by the actions.close_listing() view when the seller closes the listing early.

    Args:
            listing_id (int): the id of the listing
    Returns: None

    Called by: actions.close_listing()
    Function Calls: send_early_closing_fee_message()
    '''

    listing = Listing.objects.get(pk=listing_id)
    site_account = User.objects.get(pk=12)
    seller = listing.user
    fee_amount = round(listing.starting_bid * decimal.Decimal(0.05), 2)
    if seller.balance < fee_amount:
        amount_paid = seller.balance
        seller.balance -= fee_amount
        seller.save()

        site_account.balance += amount_paid
        now = timezone.now()
        
        if seller.fee_failure_date == None:
            seller.fee_failure_date = now

        seller.save()
        a_msg.send_fee_failure_message(listing, fee_amount)
        return False
    else:
        seller.balance -= fee_amount
        seller.save()
        site_account.balance += fee_amount
        site_account.save()

        Transaction.objects.create(
            sender=seller,
            recipient=site_account,
            amount=fee_amount,
            listing=listing,
            notes="Early Closing Fee"
        )

        a_msg.send_early_closing_fee_message(listing_id, seller.id, fee_amount)



# actions.withdraw
def validate_withdrawal_request(request, amount):
    current_user = request.user
    all_user_active_bids = Bid.objects.filter(user=current_user, listing__active=True)
    all_listings_bid_on = list(set([bid.listing for bid in all_user_active_bids]))

    # filter only listings closing in less than 72 hours
    all_listings_72 = [listing for listing in all_listings_bid_on if listing.closing_date - timezone.now() < timezone.timedelta(hours=72)]
    total_funds_72 = 0
    for listing in all_listings_72:
        total_funds_72 += Bid.objects.filter(listing=listing, user=current_user).order_by("-amount").first().amount

    # filter only listings closing in less than 24 hours
    all_listings_24 = [listing for listing in all_listings_bid_on if listing.closing_date - timezone.now() < timezone.timedelta(hours=24)]
    total_funds_24 = 0
    for listing in all_listings_24:
        total_funds_24 += Bid.objects.filter(listing=listing, user=current_user).order_by("-amount").first().amount
    
    all_listings_72.sort(key=lambda x: x.closing_date)
    first_listing_to_close = all_listings_72[0]

    if current_user.balance - amount < total_funds_24:
        return "denied", total_funds_24, total_funds_72, first_listing_to_close
    elif current_user.balance - amount < total_funds_72:
        return "warn", total_funds_24, total_funds_72, first_listing_to_close
    else:
        return "approved", total_funds_24, total_funds_72, first_listing_to_close
    


# HELPER FUNCTIONS - VIEWS.PY

# views.listing() 
def get_listing_values(request, listing):
    '''
    This function retrieves the winner, user's bid, difference between user's bid and
    the current price, and whether the listing is on the user's watchlist. It is called
    by the views.listing view to provide additional information to the listing.html template.

    Args: 
            request (HttpRequest): the request object,
            listing (Listing): the listing object
    Returns:
            winner (User): the winner of the listing,
            user_bid (Bid): the user's highest bid,
            difference (decimal): the difference between the user's bid and the current price,
            watchlist_item (Watchlist): the watchlist item if it exists, otherwise "not on watchlist"
    
    Called by: views.listing
    Function Calls: None
    '''
    
    winner = None
    user_bid = None
    difference = None


    try:
        winner = listing.winner
    except AttributeError:
        pass 
    try:
        user_bid = Bid.objects.filter(listing=listing, user=request.user).order_by("-amount").first()
    except Exception as e:
        pass 

    if user_bid:
        difference = listing.price - user_bid.amount

    if request.user.is_authenticated:
        try:
            watchlist_item = Watchlist.objects.filter(user=request.user, listing=listing)
            if not watchlist_item:
                watchlist_item = "not on watchlist"
            else:
                watchlist_item = "on watchlist"
        except Watchlist.DoesNotExist:
            pass
            
    return winner, user_bid, difference, watchlist_item


# views.listing() - calculate_time_left -> check_expiration -> declare_winner
def calculate_time_left(listing_id):
    '''
    This function calculates the time left on a listing and returns a string
    that in a format that is expected by my JavaScript countdown timer, which
    looks for a string in the format "days, hours, minutes, seconds" or a string
    that begins with "Listing" to determine what to display.

    Args:
            listing_id (int): the id of the listing
    Returns:
            string: the time left on the listing in the format "days, hours, minutes, seconds"

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

    Args: 
            listing_id (int): the id of the listing
    Returns:
            string: "active", "closed - expired", "closed - by seller"

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

    Args: 
            listing (Listing): the listing object

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
        
        
# views.listing() - check_valid_bid -> place_bid -> check_bids_funds
@login_required
def check_valid_bid(request, listing_id, amount):
    '''
    Users are only permitted to place bids within 24 hours of the listing's closing date 
    if they have sufficient funds to cover the bid. This function checks these conditions,
    then calls the place_bid function if the conditions are met.

    Args:
            request (HttpRequest): the request object,
            listing_id (int): the id of the listing,
            amount (decimal): the amount of the bid

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
    
    Args: 
            request (HttpRequest): the request object,
            amount (decimal): the amount of the bid,
            listing_id (int): the id of the listing
    Returns:
            listing (Listing): the listing object

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
                a_msg.message_previous_high_bidder(listing_id, previous_high_bidder, previous_high_bid)

        # Should never execute this block unless database error. Status will only be false if no bids exist
        # or if bid slipped through check_valid_bid()'s <24hr & <bid amount check
        elif status == False:
            logger.error(f"(Err01989)Unexpected error placing bid - bidder {current_user.name} - listing ID {listing.id} - amount {format_as_currency(amount)}")
            contrib_messages.add_message(request, contrib_messages.ERROR, f"Unexpected error placing bid. Please try again. If this issue persists, contact the admins.")
            return listing

        # Automatically add the item to the user's watchlist 
        if check_if_watchlist(request, listing) == False:
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

    Args:
            request (HttpRequest): the request object,
            listing_id (int): the id of the listing
    Returns:
            boolean: True if bid is valid and fully funded, False if bid is not fully funded
            listing (Listing): the listing object

    Called by: place_bid()
    Function Calls: send_bid_success_message_bidder(), send_bid_success_message_low_funds()
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

@login_required
def check_if_watchlist(request, listing):
    '''
    This function checks if a listing is on the user's watchlist. It is called by the
    place_bid() function to automatically add the listing to the user's watchlist if it
    is not already there.

    Args:
            user (User): the user object,
            listing (Listing): the listing object
    Returns:
            boolean: True if the listing is on the user's watchlist, False if the listing is not

    Called by: place_bid()
    Function Calls: None
    '''

    watchlist_item = Watchlist.objects.filter(user=request.user, listing=listing)
    if watchlist_item.exists():
        return True
    else:
        return False


# views.messages(), actions.sort_messages()
def set_message_sort(sort_by_direction, sent_messages, inbox_messages):
    '''
    This function sets the sort order for the user's sent and inbox messages. It is called
    by the views.messages view when the page is loaded, and called by the actions.sort_messages()
    function when the user clicks the "Sort" button. 

    Args: 
            sort_by_direction (str): the current sort order,
            sent_messages (QuerySet): the user's sent messages,
            inbox_messages (QuerySet): the user's inbox messages
    Returns:
            sent_messages (QuerySet): the user's sent messages,
            inbox_messages (QuerySet): the user's inbox messages,
            sort_by_direction (str): the new sort order
    
    Called by: views.messages(), actions.sort_messages()
    Function Calls: None
    '''

    date = "date" if sort_by_direction == "oldest-first" else "-date"
    sent_messages = sent_messages.order_by(date)
    inbox_messages = inbox_messages.order_by(date)

    return sent_messages, inbox_messages, sort_by_direction


# views.messages()
def show_hide_read_messages(request):  
    '''
    This function toggles the display of read messages in the user's inbox. It is called
    by the views.messages view when the user clicks the "Show Read" button. It sets the
    show_read session variable to the opposite of its current value.

    Args: 
            request (HttpRequest): the request object
    Returns:
            sent_messages (QuerySet): the user's sent messages,
            inbox_messages (QuerySet): the user's inbox messages,
            show_read_messages (bool): the new value of the show_read session variable

    Called by: views.messages() 
    Function Calls: None
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


# views.profile()
def check_if_old_bid(bid, listing):
    '''
    This function checks if a bid is old. A bid is considered old if it is less than the
    current price of the listing and less than the user's highest bid on the listing. It    
    is called by the create_bid_info_object_list() function to determine if a bid is old.

    Args:
            bid (Bid): the bid object,
            listing (Listing): the listing object
    Returns:
            boolean: True if the bid is old, False if the bid is not old

    Called by: create_bid_info_object_list()
    Function Calls: None
    '''

    user_bids = Bid.objects.filter(user=bid.user, listing=listing)
    if user_bids.exists():
        user_highest_bid = user_bids.order_by("-amount").first()
        if bid.amount < listing.price and bid.amount < user_highest_bid.amount:
            return True
        else:
            return False
    else:
        return False


# views.profile()
def create_bid_info_object_list(user_active_bids):
    '''
    Create a list of UserBidInfo objects to pass to the profile view. These objects
    provide additional information used in profile.html template. 

    Args: 
            user_active_bids (QuerySet): the user's active bids
    Returns:
            bid_info_list (list): a list of UserBidInfo objects

    Called by: views.profile
    Function Calls: check_if_old_bid()
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
    return sorted(bid_info_list, key=lambda x: x.user_bid.listing.date)




# MONEY TRANSFER FUNCTIONS

def transfer_to_escrow(winner, listing_id):
    '''
    This function transfers the winning bid amount from the winner's account to the escrow account.
    It is called by the declare_winner() function when a listing closes and a winner is declared.

    Args:
            winner (User): the winner of the listing,
            listing_id (int): the id of the listing
    Returns: None

    Called by: declare_winner(), actions.move_to_escrow(), tasks.check_listing_expiration()
    Function Calls: get_escrow_fail_message(), get_escrow_success_message(), send_message()
    '''

    listing = Listing.objects.get(pk=listing_id)
    buyer = winner.user
    amount = listing.price
    escrow_account = User.objects.get(pk=11)
    site_account = User.objects.get(pk=12)

    if amount > buyer.balance: 
        if listing.in_escrow == False:
            subject, message = a_msg.get_escrow_fail_message(listing)
        else: 
            logger.error(f"""(Err01989) Unexpected conflict with escrow status for {listing.title}. Expected 
                         {listing.in_escrow} to be False, but it is {listing.in_escrow}""")
    else:
        try:
            Transaction.objects.create(
                sender=buyer,
                recipient=escrow_account,
                amount=amount,
                listing=listing,
                notes="Buyer to Escrow Transfer"
            )

            buyer.balance -= amount
            buyer.save()
            escrow_account.balance += amount
            escrow_account.save()
            listing.in_escrow = True
            listing.save()
        except (IntegrityError, ValueError) as e:
            logger.error(f"(Err01989) Unexpected error transferring funds to escrow account: {e}")

        subject, message = a_msg.get_escrow_success_message(listing)

    a_msg.send_message(site_account, buyer, subject, message)
    

def transfer_to_seller(listing_id):
    '''
    This function transfers the winning bid amount from the escrow account to the seller's account.
    It is called by the actions.confirm_shipping() function when the seller confirms that the item has
    been shipped.

    Args:
            listing_id (int): the id of the listing
    Returns: None

    Called by: actions.confirm_shipping()
    Function Calls: send_message()
    '''
    
    listing = Listing.objects.get(pk=listing_id)
    seller = listing.user
    sale_price = listing.price
    escrow_account = User.objects.get(pk=11)
    site_account = User.objects.get(pk=12)

    if listing.in_escrow == True:
        if sale_price > escrow_account.balance:
            # Send Alert Message to Admin if escrow account is empty when it shouldn't be
            a_msg.send_escrow_empty_alert_message(listing.id)
            logger.error(f"(Err01989) Escrow account is empty for {listing.title}")
            return False
        else:
            fee_amount = round(sale_price * decimal.Decimal(0.10), 2)
            sale_price -= fee_amount

            # Create Transaction objects for the fee and the sale
            fee_transaction = Transaction.objects.create(
                sender=escrow_account,
                recipient=site_account,
                amount=fee_amount,
                listing=listing,
                notes="Sale Fee"
            )
            fee_transaction.save()

            sell_transaction = Transaction.objects.create(
                sender=escrow_account,
                recipient=seller,
                amount=sale_price,
                listing=listing,
                notes="Escrow to Seller Transfer"
            )
            sell_transaction.save()

            # Update the balances for the seller and the escrow account
            escrow_account.balance -= sale_price
            escrow_account.save()
            seller.balance += sale_price
            seller.save()

            listing.in_escrow = False

            # Send confirmation message to seller and buyer after shipping confirmed
            a_msg.send_shipping_confirmation_messages(listing.id)

            return True
    else:
        logger.error(f"(Err01989) Unexpected conflict with escrow status for {listing.title}")
        return False