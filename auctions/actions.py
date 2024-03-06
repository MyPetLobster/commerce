from django.contrib import messages as contrib_messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse

import decimal
import logging

from . import helpers
from .classes import UserInfoForm
from .models import Bid, Listing, Watchlist, User, Message, Comment, Transaction
from .tasks import notify_all_closed_listing, transfer_to_escrow, transfer_to_seller


logger = logging.getLogger(__name__)


# INDEX/LISTINGS FUNCTIONS
def sort(request):
    # Sort Form Fields: Title, Seller, Date, Price
    # Sort Order: Ascending, Descending
    page = request.POST["page"]
    sort_by = request.POST["sort-by"]
    sort_by_direction = request.POST["sort-by-direction"]


    listings = Listing.objects.all()

    if sort_by == "title":
        if sort_by_direction == "asc":
            listings = listings.order_by("title")
        else:
            listings = listings.order_by("-title")
    elif sort_by == "seller":
        if sort_by_direction == "asc":
            listings = listings.order_by("user")
        else:
            listings = listings.order_by("-user")
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
    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()

    if page == "index":
        return render(request, "auctions/index.html", {
            "listings": listings,
            "current_user": current_user,
            "messages": messages,
            "unread_message_count": unread_message_count
        })
    elif page == "listings":
        return render(request, "auctions/listings.html", {
            "listings": listings,
            "current_user": current_user,
            "messages": messages,
            "unread_message_count": unread_message_count
        })
    



# LISTING FUNCTIONS
@login_required
def add_to_watchlist(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    watchlist_item, created = Watchlist.objects.get_or_create(user=request.user, listing=listing)
    if created:
        return HttpResponseRedirect(reverse("listing", args=(listing_id,)))
    else:
        listings = Listing.objects.all()
        current_user = request.user
        contrib_messages.add_message(request, contrib_messages.ERROR, "Listing already on watchlist")
        messages = contrib_messages.get_messages(request)
        unread_messages = Message.objects.filter(recipient=current_user, read=False)
        unread_message_count = unread_messages.count()
        return render(request, "auctions/index.html" , {
            "listings": listings,
            "current_user": current_user,
            "messages": messages,
            "unread_message_count": unread_message_count
        })


@login_required
def remove_from_watchlist(request, listing_id):
    try:
        watchlist_item = Watchlist.objects.get(user=request.user, listing_id=listing_id)
        watchlist_item.delete()
    except Watchlist.DoesNotExist:
        contrib_messages.add_message(request, contrib_messages.ERROR, "Listing not on watchlist")
    return HttpResponseRedirect(reverse("listing", args=(listing_id,)))
    

@login_required
def close_listing(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    if request.user == listing.user:
        highest_bid = Bid.objects.filter(listing=listing).order_by("-amount").first()
        starting_bid = listing.starting_bid
        try:
            if highest_bid.amount > starting_bid:
                try:
                    listing.winner = highest_bid.user
                    listing.save()
                    winner = listing.winner
                    transfer_to_escrow(winner)
                    notify_all_closed_listing(listing.id)
                    listing.active = False
                    listing.save()
                except:
                    listing.winner = None
                    listing.active = True
                    listing.save()
                    contrib_messages.error(request, "Unexpected error closing listing, contact admins.")
                    return HttpResponseRedirect(reverse("index"))

            else:
                listing.cancelled = True
                listing.active = False
                listing.save()

            
        except:
            contrib_messages.error(request, "Unexpected error closing listing, contact admins.")
    return HttpResponseRedirect(reverse("index"))


@login_required
def comment(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    comment = request.POST["comment"]
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
    return HttpResponseRedirect(reverse("listing", args=(listing_id,)))


@login_required
def move_to_escrow(request, listing_id):
    current_user = request.user
    listing = Listing.objects.get(pk=listing_id)
    winner = listing.winner

    if winner == current_user:
        if listing.active == False and listing.in_escrow == False and listing.shipped == False:
            transfer_to_escrow(winner, listing_id)
            
    return HttpResponseRedirect(reverse("listing", args=(listing_id,)))


# PROFILE FUNCTIONS
@login_required
def edit(request, user_id):
    user = User.objects.get(pk=user_id)
    form = UserInfoForm(request.POST, instance=user)
    if form.is_valid():
        form.save()
        return redirect("profile", user_id=user_id)
    else:
        return render(request, "auctions/profile.html", {
            "user_info_form": form
        })
    

@login_required
def change_password(request, user_id):
    user = User.objects.get(pk=user_id)

    old_password = request.POST["old_password"]
    new_password = request.POST["new_password1"]
    new_password_confirm = request.POST["new_password2"]

    if not user.check_password(old_password):
        contrib_messages.error(request, "Old password is incorrect")
        return redirect("profile", user_id=user_id)

    if new_password != new_password_confirm:
        contrib_messages.error(request, "Passwords do not match")
        return redirect("profile", user_id=user_id)
    
    user.set_password(new_password)
    user.save()
    
    contrib_messages.success(request, "Password changed successfully")
    return render(request, "auctions/profile.html", {
        "user_id": user_id,
        "current_user": request.user
    })




# Profile - Money Related Functions
@login_required
def deposit(request, user_id):
    fake_bank_account = User.objects.get(pk=13)
    user = User.objects.get(pk=user_id)
    amount = request.POST["amount"]
    amount = decimal.Decimal(amount)
    if amount <= 0:
        contrib_messages.error(request, "Deposit amount must be greater than 0")
        return redirect("profile", user_id=user_id)
    
    Transaction.objects.create(
        amount=amount,
        sender=fake_bank_account,
        recipient=user
    )

    fake_bank_account.balance -= decimal.Decimal(amount)
    fake_bank_account.save()
    user.balance += decimal.Decimal(amount)
    user.save()
    return redirect("profile", user_id=user_id)


@login_required
def withdraw(request, user_id):
    fake_bank_account = User.objects.get(pk=13)
    user = User.objects.get(pk=user_id)
    amount = request.POST["amount"]
    amount = decimal.Decimal(amount)
    if amount <= 0:
        contrib_messages.error(request, "Withdrawal amount must be greater than 0")
        return redirect("profile", user_id=user_id)
    if amount > user.balance:
        contrib_messages.error(request, "Insufficient funds")
        return redirect("profile", user_id=user_id)
    
    Transaction.objects.create(
        amount=amount,
        sender=user,
        recipient=fake_bank_account
    )

    fake_bank_account.balance += amount
    fake_bank_account.save()
    user.balance -= amount
    user.save()
    return redirect("profile", user_id=user_id)


@login_required
def confirm_shipping(request, listing_id):
    '''
    Seller will have a button on profile to confirm shipping once the 
    winner's funds have been transferred to escrow.

    Once pressed, money will be transferred from escrow to seller.
    '''
    listing = Listing.objects.get(pk=listing_id)
    if listing.shipped == False:
        if transfer_to_seller(listing_id):
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
    current_user = request.user
    
    if request.method == "POST":
        sort_by_direction = request.POST["sort-by-direction"]
        request.session["sort_by_direction"] = sort_by_direction

    sent_messages, inbox_messages, show_read_messages = helpers.show_hide_read_messages(request)
    sent_messages, inbox_messages, sort_by_direction = helpers.determine_message_sort(request, sent_messages, inbox_messages)

    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()

    return render(request, "auctions/messages.html", {
        'sent_messages': sent_messages,
        'inbox_messages': inbox_messages,
        'current_user': current_user,
        'messages': messages,
        'unread_message_count': unread_message_count,
        'sort_by_direction': sort_by_direction,
        'show_read_messages': show_read_messages
    })


def mark_as_read(request, message_id):
    message = Message.objects.get(pk=message_id)
    if message.read == False:
        message.read = True
    else:
        message.read = False
    message.save()
    return HttpResponseRedirect(reverse("messages", args=(request.user.id,)))


def mark_all_as_read(request, user_id):
    messages = Message.objects.filter(recipient=request.user)
    for message in messages:
        message.read = True
        message.save()
    return HttpResponseRedirect(reverse("messages", args=(user_id,)))


def delete_message(request, message_id):
    current_user = request.user
    message = Message.objects.get(pk=message_id)
    message.deleted_by.add(current_user)
    message.save()
    return HttpResponseRedirect(reverse("messages", args=(request.user.id,)))


