from django.contrib import messages as contrib_messages
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

import decimal
import logging

from . import auto_messages as a_msg
from . import helpers
from .classes import UserInfoForm
from .models import Bid, Listing, Watchlist, User, Message, Comment, Transaction


logger = logging.getLogger(__name__)




# INDEX/LISTINGS FUNCTIONS
def sort(request):
    '''
    This function is called when the user clicks on the sort button in the index or listings page.
    It sorts the listings based on the sort_by and sort_by_direction form fields and then redirects
    to the index or listings page.

    Form Fields (POST): title, seller, date, price
    Sort Order (POST): asc, desc

    Args: 
            request (HttpRequest): The request object
    Returns: 
            HttpResponseRedirect: Redirects to the index or listings page

    Called by: index.html, listings.html
    Functions Called: None
    '''

    page = request.POST["page"]
    sort_by = request.POST["sort-by"]
    sort_by_direction = request.POST["sort-by-direction"]

    listings = Listing.objects.all()

    if sort_by == "title":
        if sort_by_direction == "asc":
            listings = listings.annotate(title_lower=Lower('title')).order_by("title_lower")
        else:
            listings = listings.annotate(title_lower=Lower('title')).order_by("-title_lower")
    elif sort_by == "seller":
        if sort_by_direction == "asc":
            listings = listings.annotate(user_lower=Lower('user__username')).order_by("user_lower")
        else:
            listings = listings.annotate(user_lower=Lower('user__username')).order_by("-user_lower")
    elif sort_by == "date":
        if sort_by_direction == "asc":
            listings = listings.order_by("date")
        else:
            listings = listings.order_by("-date")
    elif sort_by == "price":
        if sort_by_direction == "asc":
            listings = listings.order_by("price")
        else:
            listings = listings.order_by("-price")
    else:
        listings = listings
    
    current_user = request.user
    render_vals = {
        "listings": listings,
        "current_user": current_user,
        "messages": contrib_messages.get_messages(request),
        "unread_message_count": Message.objects.filter(recipient=current_user, read=False).count()
    }
    if page == "index":
        return render(request, "auctions/index.html", render_vals)
    elif page == "listings":
        return render(request, "auctions/listings.html", render_vals)
    



# LISTING FUNCTIONS
@login_required
def add_to_watchlist(request, listing_id):
    ''' 
    This function is called when the user clicks the "Add to Watchlist" button on the listing page.
    It creates a new watchlist item in the database and redirects to the listing page.

    Args: 
            request (HttpRequest): The request object
            listing_id (int): The ID of the listing to be added to the watchlist
    Returns: 
            HttpResponseRedirect: Redirects to the listing page
    Called by: listing.html
    Functions Called: None
    '''

    listing = Listing.objects.get(pk=listing_id)
    watchlist_item, created = Watchlist.objects.get_or_create(user=request.user, listing=listing)
    if created:
        return HttpResponseRedirect(reverse("listing", args=(listing_id,)))
    else:
        contrib_messages.add_message(request, contrib_messages.ERROR, "Listing already on watchlist")
        return HttpResponseRedirect(reverse("listing", args=(listing_id,)))


@login_required
def remove_from_watchlist(request, listing_id):
    '''
    This function is called when the user clicks the "Remove from Watchlist" button on the listing page 
    or the watchlist page. It deletes the watchlist item from the database and redirects to the page
    the user clicked from.
    
    Args: 
            request (HttpRequest): The request object
            listing_id (int): The ID of the listing to be removed from the watchlist
    Returns: 
            HttpResponseRedirect: Redirects to the listing or watchlist page
    Called by: listing.html, watchlist.html
    Functions Called: None
    '''

    try:
        watchlist_item = Watchlist.objects.get(user=request.user, listing_id=listing_id)
        watchlist_item.delete()
    except Watchlist.DoesNotExist:
        contrib_messages.add_message(request, contrib_messages.ERROR, "Listing not on watchlist")
    clicked_from = request.POST["clicked-from"]

    if clicked_from == "listing":
        return HttpResponseRedirect(reverse("listing", args=(listing_id,)))
    elif clicked_from == "watchlist":
        return HttpResponseRedirect(reverse("watchlist"))
    else:
        logger.error(f"(Err22222) Invalid or missing 'clicked-from' value in the request")
        raise Http404("Invalid or missing 'clicked-from' value in the request")
    

@login_required
def close_listing(request, listing_id):
    '''
    This function is called when the seller clicks the "Close Listing" button on the listing page.
    It checks if the listing has any active bids. If there are active bids, it sets the closing_date
    to 24 hours from the current time and returns to the listing page. If there are no active bids, it
    charges the early closing fee and sets the listing to inactive and cancelled. Users cannot close a
    listing with less than 24 hours remaining.

    Args: 
            request (HttpRequest): The request object
            listing_id (int): The ID of the listing to be closed
    Returns: 
            HttpResponseRedirect: Redirects to the index page

    Called by: listing.html
    Functions Called: charge_early_closing_fee, notify_all_early_closing
    '''

    try:
        listing = Listing.objects.get(pk=listing_id)
        
        # Only the seller can close the listing
        if request.user != listing.user:
            contrib_messages.error(request, "You cannot close a listing that you did not create.")
            return HttpResponseRedirect(reverse("listing", args=(listing_id,)))
        
        starting_bid = listing.starting_bid
        highest_bid = Bid.objects.filter(listing=listing).order_by("-amount").first()
        highest_bid = highest_bid.amount if highest_bid else starting_bid

        if listing.closing_date - timezone.now() < timezone.timedelta(hours=24):
            # If there are less than 24 hours left, the listing cannot be closed manually
            contrib_messages.error(request, "Listing cannot be closed with less than 24 hours remaining.")
            return HttpResponseRedirect(reverse("listing", args=(listing_id,)))

        if highest_bid > starting_bid:
            # If there are active bids, there will be 24 hour delay before closing
            listing.closing_date = timezone.now() + timezone.timedelta(hours=24)
            listing.save()
            contrib_messages.info(request, "You have active bids on this listing. There will be a 24 hour delay before closing.")
            a_msg.notify_all_early_closing(listing.id)
            return HttpResponseRedirect(reverse("listing", args=(listing_id,)))
        else:
            # No bids, charge early closing fee and close listing
            helpers.charge_early_closing_fee(listing_id)
            listing.cancelled = True
            listing.active = False
            listing.save()

    except Listing.DoesNotExist:
        logger.error(f"(Err22222) Unexpected error closing listing ID {listing_id}. Listing does not exist.")
        contrib_messages.error(request, "Unexpected error closing listing, contact admins.")

    except Exception as e:
        logger.error(f"(Err01989) Unexpected error closing listing ID {listing_id}. {e}")
        contrib_messages.error(request, "Unexpected error closing listing, contact admins.")

    return HttpResponseRedirect(reverse("index"))


@login_required
def comment(request, listing_id):
    '''
    This function is called when a user submits a comment on a listing page. It creates a new comment
    object and saves it to the database. It then calls the notify_mentions function to notify any
    mentioned users.
    
    Args: 
            request (HttpRequest): The request object
            listing_id (int): The ID of the listing to comment on   
    Returns: 
            HttpResponseRedirect: Redirects to the listing page

    Called by: listing.html
    Functions Called: notify_mentions()
    '''

    listing = Listing.objects.get(pk=listing_id)
    comment = helpers.filter_profanity(request.POST["comment"])
    anonymous = request.POST.get("anonymous", "off")

    if anonymous == "on":
        anonymous = True
    else:
        anonymous = False
    
    comment = Comment.objects.create(
        comment=comment,
        anonymous=anonymous,
        listing=listing,
        user=request.user
    )

    a_msg.notify_mentions(comment)

    return HttpResponseRedirect(reverse("listing", args=(listing_id,)))


@login_required
def delete_comment(request, comment_id):
    '''
    This function is called when a user clicks the "Delete" button on a comment. It deletes the comment
    from the database and then redirects to the listing page. User can only delete their own comments.

    Args: 
            request (HttpRequest): The request object
            comment_id (int): The ID of the comment to delete   
    Returns: 
            HttpResponseRedirect: Redirects to the listing page

    Called by: listing.html
    Functions Called: None
    '''
    comment = Comment.objects.get(pk=comment_id)
    listing_id = comment.listing.id
    if request.user == comment.user:
        comment.delete()

    return HttpResponseRedirect(reverse("listing", args=(listing_id,)))


@login_required
def move_to_escrow(request, listing_id):
    '''
    This function is called when the seller clicks the "Move to Escrow" button on the listing page.
    The option will only be available to users who are the winner of a listing and for whom the 
    automatic transfer to escrow failed. It calls the transfer_to_escrow function to transfer the
    winner's funds to escrow.

    Args: 
            request (HttpRequest): The request object
            listing_id (int): The ID of the listing to be moved to escrow   
    Returns: 
            HttpResponseRedirect: Redirects to the listing page

    Called by: listing.html
    Functions Called: transfer_to_escrow()

    *Note* This is not the same as the transfer_to_escrow() function
    '''

    current_user = request.user
    listing = Listing.objects.get(pk=listing_id)
    winner = listing.winner

    if winner == current_user:
        if listing.active == False and listing.in_escrow == False and listing.shipped == False:
            helpers.transfer_to_escrow(winner, listing_id)
            
    return HttpResponseRedirect(reverse("listing", args=(listing_id,)))


@login_required
def cancel_bid(request, listing_id):
    '''
    This function is called when a user clicks the "Cancel Bid" button on the listing page. It deletes
    all of the user's bids on the listing and then calls functions to notify all parties involved.

    Args: 
            request (HttpRequest): The request object
            listing_id (int): The ID of the listing to cancel the bid on
    Returns: 
            HttpResponseRedirect: Redirects to the listing page

    Called by: listing.html
    Functions Called: send_bid_cancelled_message_confirmation(), send_bid_cancelled_message_new_high_bidder(),
                        get_bid_cancelled_message_seller_bids(), get_bid_cancelled_message_seller_no_bids(),
                        send_message()
    '''

    current_user = request.user
    listing = Listing.objects.get(pk=listing_id)

    all_user_bids_for_listing = Bid.objects.filter(user=current_user, listing=listing)

    if listing.active == True and listing.closing_date - timezone.now() > timezone.timedelta(hours=24):
        for bid in all_user_bids_for_listing:
            bid.delete()

        site_account = User.objects.get(pk=12)
        seller = listing.user
        all_bids_on_listing = Bid.objects.filter(listing=listing).order_by("-amount")
        
        
        if all_bids_on_listing:
            highest_bid = all_bids_on_listing.first()
            
            listing.price = highest_bid.amount
            listing.save()

            a_msg.send_bid_cancelled_message_confirmation(request, listing.id)
            a_msg.send_bid_cancelled_message_new_high_bidder(request, listing.id, highest_bid)
            subject_seller, message_seller = a_msg.get_bid_cancelled_message_seller_bids(request, listing.id, highest_bid)   
        else: 
            listing.price = listing.starting_bid
            listing.save()
            subject_seller, message_seller = a_msg.get_bid_cancelled_message_seller_no_bids(request, listing.id)

        a_msg.send_message(site_account, seller, subject_seller, message_seller)
    else:
        contrib_messages.error(request, "Cannot cancel bid with less than 24 hours remaining.")

    return HttpResponseRedirect(reverse("listing", args=(listing_id,)))


@login_required
def report_comment(request, comment_id):
    '''
    This function is called when the user clicks the "Report" button on a comment. 
    '''
    current_user = request.user
    reason = request.POST["reason"]
    comment = Comment.objects.get(pk=comment_id)
    a_msg.send_comment_report_admin(current_user, comment, reason)

    return HttpResponseRedirect(reverse("listing", args=(comment.listing.id,)))


@login_required
def report_listing(request, listing_id):
    '''
    This function is called when the user clicks the "Report" button on a listing. 
    '''
    current_user = request.user
    reason = request.POST["reason"]
    listing = Listing.objects.get(pk=listing_id)
    a_msg.send_listing_report_admin(current_user, listing, reason)

    return HttpResponseRedirect(reverse("listing", args=(listing_id,)))



# PROFILE FUNCTIONS

# Profile - Report User
@login_required
def report_user(request, user_id):
    '''
    This function is called when the user clicks the "Report" button on the profile page. 
    '''
    current_user = request.user
    reason = request.POST["reason"]
    reported_user = User.objects.get(pk=user_id)
    a_msg.send_user_report_admin(current_user, reported_user, reason)

    return HttpResponseRedirect(reverse("profile", args=(user_id,)))

# Profile - User Info Related Actions
@login_required
def edit(request, user_id):
    '''
    This function is called when the user clicks the "Edit" button on the profile page. It renders the
    profile.html template with the user_info_form form. If the form is valid, it saves the changes to
    the user object and redirects to the profile page. If the form is invalid, it adds an error message
    and redirects to the profile page.

    Args: 
            request (HttpRequest): The request object
            user_id (int): The ID of the user to edit
    Returns: 
            HttpResponseRedirect: Redirects to the profile page

    Called by: profile.html
    Functions Called: None
    '''

    user = User.objects.get(pk=user_id)
    form = UserInfoForm(request.POST, instance=user)
    if form.is_valid():
        form.save()
        return redirect("profile", user_id=user_id)
    else:
        contrib_messages.error(request, "Invalid form data")
        return redirect("profile", user_id=user_id)
    

@login_required
def change_password(request, user_id):
    '''
    This function is called when the user submits the change password form on the profile page. It
    checks if the old password is correct and if the new password and new password confirm match.
    If the old password is incorrect, it adds an error message and redirects to the profile page. 
    It also checks a number of other password requirements and adds error messages if they are not met.
    
    Args: 
            request (HttpRequest): The request object
            user_id (int): The ID of the user to change the password for
    Returns: 
            HttpResponseRedirect: Redirects to the profile page

    Called by: profile.html
    Functions Called: None
    '''

    user = User.objects.get(pk=user_id)

    old_password = request.POST["old_password"]
    new_password = request.POST["new_password1"]
    new_password_confirm = request.POST["new_password2"]

    if not user.check_password(old_password):
        contrib_messages.error(request, "Old password is incorrect")
    elif new_password != new_password_confirm:
        contrib_messages.error(request, "Passwords do not match")
        return redirect("profile", user_id=user_id)
    elif new_password == old_password:
        contrib_messages.error(request, "New password cannot be the same as old password")
        return redirect("profile", user_id=user_id)
    elif len(new_password) < 8:
        contrib_messages.error(request, "Password must be at least 8 characters long")
        return redirect("profile", user_id=user_id)
    elif new_password.isalpha() or new_password.isdigit():
        contrib_messages.error(request, "Password must contain at least one letter and one number")
    else: 
        contrib_messages.success(request, "Password changed successfully")
        user.set_password(new_password)
        user.save()

    return redirect("profile", user_id=user_id)


@login_required
def delete_account(request, user_id):
    '''
    This function is called when the user clicks the "Delete Account" button on the profile page. It
    checks if the user has any active listings or bids. If they do, it adds an error message and
    redirects to the profile page. If they do not, it deletes the user and redirects to the index page.

    Args:
            request (HttpRequest): The request object
            user_id (int): The ID of the user to delete
    Returns:
            HttpResponseRedirect: Redirects to the index page

    Called by: profile.html
    Functions Called: None
    '''

    user = User.objects.get(pk=user_id)
    user_listings = Listing.objects.filter(user=user)
    user_bids = Bid.objects.filter(user=user)

    for listing in user_listings:
        if listing.active == True:
            contrib_messages.error(request, "Cannot delete account with active listings")
            return redirect("profile", user_id=user_id)
    for bid in user_bids:
        if bid.listing.active == True:
            contrib_messages.error(request, "Cannot delete account with active bids")
            return redirect("profile", user_id=user_id)

    user.delete()
    return redirect("index")


# Profile - Money Related Actions
@login_required
def deposit(request, user_id):
    '''
    This function is called when the user submits the deposit form on the profile page. It creates a
    new transaction object and updates the user's balance. It then redirects to the profile page.

    Args:
            request (HttpRequest): The request object
            user_id (int): The ID of the user to deposit money for
    Returns:
            HttpResponseRedirect: Redirects to the profile page

    Called by: profile.html
    Functions Called: None
    '''

    fake_bank_account = User.objects.get(pk=13)
    user = User.objects.get(pk=user_id)
    amount = decimal.Decimal(request.POST["amount"])

    if amount <= 0:
        contrib_messages.error(request, "Deposit amount must be greater than 0")
        return redirect("profile", user_id=user_id)
    
    Transaction.objects.create(
        amount=amount,
        sender=fake_bank_account,
        recipient=user,
        notes="Deposit"
    )

    fake_bank_account.balance -= decimal.Decimal(amount)
    fake_bank_account.save()
    user.balance += decimal.Decimal(amount)
    user.save()
    contrib_messages.success(request, "Deposit successful")

    return redirect("profile", user_id=user_id)


@login_required
def withdraw(request, user_id):
    '''
    This function is called when the user submits the withdraw form on the profile page. It creates a
    new transaction object and updates the user's balance. It then redirects to the profile page.

    Args:
            request (HttpRequest): The request object
            user_id (int): The ID of the user to withdraw money from
    Returns:
            HttpResponseRedirect: Redirects to the profile page

    Called by: profile.html
    Functions Called: None
    '''

    fake_bank_account = User.objects.get(pk=13)
    user = User.objects.get(pk=user_id)
    amount = decimal.Decimal(request.POST["amount"])
    if amount <= 0:
        contrib_messages.error(request, "Withdrawal amount must be greater than 0")
    elif amount > user.balance:
        contrib_messages.error(request, "Insufficient funds")
    else:
        status, total_funds_24, total_funds_72, first_listing_to_close = helpers.validate_withdrawal(user_id, amount)

        if status == "denied":
            contrib_messages.error(request, "Insufficient funds. You have active bids closing in less than 24 hours.")
            a_msg.send_message_deny_withdrawal(request, user_id, amount, total_funds_24)
        elif status == "warn":
            contrib_messages.info(request, "Successful withdrawal, but you have active bids closing in less than 72 hours. See messages for details.")
            a_msg.send_message_withdrawal_72(request, user_id, amount, total_funds_72, first_listing_to_close)
        else:
            Transaction.objects.create(
                amount=amount,
                sender=user,
                recipient=fake_bank_account,
                notes="Withdrawal"
            )
            fake_bank_account.balance += amount
            fake_bank_account.save()
            user.balance -= amount
            user.save()
            
            contrib_messages.success(request, "Withdrawal successful")
            a_msg.send_message_withdrawal_success(user_id, amount)

    return redirect("profile", user_id=user_id)


@login_required
def confirm_shipping(request, listing_id):
    '''
    Seller will have a button on profile to confirm shipping once the winner's funds have been 
    transferred to escrow. Once pressed, money will be transferred from escrow to seller.

    Args:
            request (HttpRequest): The request object
            listing_id (int): The ID of the listing to confirm shipping for 
    Returns:
            HttpResponseRedirect: Redirects to the listing page

    Called by: profile.html
    Functions Called: transfer_to_seller()
    '''

    listing = Listing.objects.get(pk=listing_id)
    if listing.shipped == False:
        if helpers.transfer_to_seller(listing_id):
            listing.shipped = True
            listing.save()    
            contrib_messages.success(request, "Shipping confirmed")
        else:
            logger.error(f"(Err01989) Unexpected error confirming shipping for listing ID {listing_id}")
            contrib_messages.error(request, "Unexpected error confirming shipping, contact admins.")
    else:
        logger.error(f"(Err01989) Unexpected error confirming shipping for listing ID {listing_id}")
        contrib_messages.error(request, "Unexpected error confirming shipping, contact admins.")
    
    return redirect("listing", listing_id=listing_id)




# MESSAGES FUNCTIONS
def sort_messages(request):
    ''' 
    This action is called when the user clicks on the sort button in the messages page.
    It sets the sort_by_direction session variable to the value of the sort-by-direction
    form field. It then calls the show_hide_read_messages and set_message_sort functions
    to handle the sorting and filtering of messages to pass to the messages.html template.

    Args: 
        request (HttpRequest): The request object
    Returns: 
        HttpResponseRedirect: Redirects to the messages page

    Called by: messages.html
    Functions Called: show_hide_read_messages, set_message_sort 
    '''

    current_user = request.user
    
    if request.method == "POST":
        sort_by_direction = request.POST["sort-by-direction"]
        request.session["sort_by_direction"] = sort_by_direction

    sent_messages, inbox_messages, show_read_messages = helpers.show_hide_read_messages(request)
    sent_messages, inbox_messages, sort_by_direction = helpers.set_message_sort(request, sent_messages, inbox_messages)

    return render(request, "auctions/messages.html", {
        'sent_messages': sent_messages,
        'inbox_messages': inbox_messages,
        'current_user': current_user,
        'messages': contrib_messages.get_messages(request),
        'unread_message_count': Message.objects.filter(recipient=current_user, read=False).count(),
        'sort_by_direction': sort_by_direction,
        'show_read_messages': show_read_messages
    })


def mark_as_read(request, message_id):
    '''
    This function is called when the user clicks the "Mark as Read" button on the messages page.
    It toggles the read field of the message and then redirects to the messages page.

    Args:
            request (HttpRequest): The request object
            message_id (int): The ID of the message to mark as read
    Returns:
            HttpResponseRedirect: Redirects to the messages page

    Called by: messages.html    
    Functions Called: None
    '''

    message = Message.objects.get(pk=message_id)
    message.read = not message.read
    message.save()

    return HttpResponseRedirect(reverse("messages", args=(request.user.id,)))


def mark_all_as_read(request, user_id):
    '''
    This function is called when the user clicks the "Mark All as Read" button on the messages page.
    It sets the read field of all messages to True and then redirects to the messages page.

    Args:
            request (HttpRequest): The request object
            user_id (int): The ID of the user to mark all messages as read for
    Returns:
            HttpResponseRedirect: Redirects to the messages page

    Called by: messages.html
    Functions Called: None
    '''

    messages = Message.objects.filter(recipient=request.user)
    for message in messages:
        message.read = True
        message.save()
    return HttpResponseRedirect(reverse("messages", args=(user_id,)))


def delete_message(request, message_id):
    '''
    This function is called when the user clicks the "Delete" button on the messages page. It adds
    the user to the deleted_by field of the message and then redirects to the messages page. This 
    is so that the message is not deleted from the db and can still be viewed by the other party.

    Args:
            request (HttpRequest): The request object
            message_id (int): The ID of the message to delete
    Returns:
            HttpResponseRedirect: Redirects to the messages page

    Called by: messages.html
    Functions Called: None
    '''

    current_user = request.user
    message = Message.objects.get(pk=message_id)
    message.deleted_by.add(current_user)
    message.save()
    return HttpResponseRedirect(reverse("messages", args=(request.user.id,)))




# WATCHLIST FUNCTIONS
@login_required
def remove_inactive_from_watchlist(request):
    '''
    This function is called when the user clicks the "Remove Inactive Listings" button on the watchlist
    page. It deletes all watchlist items for listings that are not active and then redirects to the
    watchlist page.

    Args:
            request (HttpRequest): The request object
    Returns:
            HttpResponseRedirect: Redirects to the watchlist page

    Called by: watchlist.html
    Functions Called: None
    '''

    watchlist_items = Watchlist.objects.filter(user=request.user)
    for item in watchlist_items:
        if item.listing.active == False:
            item.delete()
    
    watchlist_items = Watchlist.objects.filter(user=request.user)
    listings = [item.listing for item in watchlist_items]
    listings.sort(key=lambda x: x.date)
    current_user = request.user
    return render(request, "auctions/watchlist.html", {
        "listings": listings,
        "current_user": current_user,
        "messages": contrib_messages.get_messages(request),
        "unread_message_count": Message.objects.filter(recipient=current_user, read=False).count(),
        "inactive_watchlist_items_count": Watchlist.objects.filter(user=current_user, listing__active=False).count()
    })








# All functions in this file:
#   - sort 
#   - add_to_watchlist
#   - remove_from_watchlist
#   - close_listing
#   - comment
#   - move_to_escrow
#   - cancel_bid
#   - edit
#   - change_password
#   - delete_account
#   - deposit
#   - withdraw
#   - confirm_shipping
#   - sort_messages
#   - mark_as_read
#   - mark_all_as_read
#   - delete_message
#   - remove_inactive_from_watchlist




# All outside functions used in this file:
#   - auto_messages.py:
#       - notify_mentions
#       - send_bid_cancelled_message_confirmation
#       - send_bid_cancelled_message_new_high_bidder
#       - get_bid_cancelled_message_seller_bids
#       - get_bid_cancelled_message_seller_no_bids
#       - send_message
#       - notify_all_early_closing

#   - helpers.py:
#       - charge_early_closing_fee
#       - transfer_to_escrow
#       - transfer_to_seller
#       - show_hide_read_messages
#       - set_message_sort