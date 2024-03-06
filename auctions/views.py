from django.contrib import messages as contrib_messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.urls import reverse
from django.utils import timezone

import decimal 
import logging
from datetime import timedelta

from . import helpers
from .models import Bid, Category, Comment, Listing, Message, Transaction, User, Watchlist
from .tasks import send_message
from .classes import CommentForm, ListingForm, UserBidInfo, UserInfoForm


logger = logging.getLogger(__name__)




# VIEWS - AUTHENTICATION
def login_view(request):
    if request.method == "POST":

        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")




def set_closing_dates_if_not_set(request):
    '''
    This view is used to set closing dates for listings that were created
    before the closing_date field was added to the Listing model. 
    '''

    listings = Listing.objects.filter(active=True)
    for listing in listings:
        if listing.closing_date == None:
            listing.closing_date = listing.date + timedelta(days=7)
            listing.save()
    return HttpResponseRedirect(reverse("index"))



# VIEWS - PUBLIC
def categories(request):
    categories = get_list_or_404(Category.objects.all())
    current_user = request.user
    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()

    return render(request, "auctions/categories.html", {
        "categories": categories,
        "current_user": current_user,
        "messages": messages,
        "unread_message_count": unread_message_count
    })


def category(request, category_id):
    listings = Listing.objects.filter(categories=category_id)
    category = get_object_or_404(Category, pk=category_id)
    current_user = request.user
    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()

    return render(request, "auctions/category.html", {
        "listings": listings,
        "category": category,
        "current_user": current_user,
        "messages": messages,
        "unread_message_count": unread_message_count
    })


def index(request):

    set_closing_dates_if_not_set(request)

    current_user = request.user
    listings = Listing.objects.all()

    if current_user.is_authenticated:
        messages = contrib_messages.get_messages(request)
        unread_messages = Message.objects.filter(recipient=current_user, read=False)
        unread_message_count = unread_messages.count()

        helpers.set_inactive(listings)
        listings = get_list_or_404(Listing.objects.all())

        return render(request, "auctions/index.html" , {
            "listings": listings,
            "current_user": current_user,
            "messages": messages,
            "unread_message_count": unread_message_count
        })
    else:   
        return render(request, "auctions/index.html" , {
            "listings": listings,
            "current_user": current_user
        })


def listings(request):
    listings = get_list_or_404(Listing.objects.all())
    current_user = request.user
    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()

    helpers.set_inactive(listings)
    listings = get_list_or_404(Listing.objects.all())

    return render(request, "auctions/listings.html", {
        "listings": listings,
        "current_user": current_user,
        "messages": messages,
        "unread_message_count": unread_message_count
    })


def listing(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    current_user = request.user

    # Calculate Time Left (7 days from listing date)    
    listing_date = listing.date
    current_date_time = timezone.now()
    diff_seconds = round((listing_date - current_date_time).total_seconds() * -1.0, 2)

    # Generate time left string for JavaScript display, live countdown
    if helpers.check_expiration(listing_id) == "closed - expired":
        closed_date = listing.date + timedelta(days=7)
        time_left = f"Listing expired on {closed_date.month}/{closed_date.day}/{closed_date.year}"
    elif helpers.check_expiration(listing_id) == "closed - by seller":
        time_left = "Listing closed by seller"
    else:
        time_left = helpers.generate_time_left_string(diff_seconds)

    # POST Request - Place Bid
    if request.method == "POST":
        amount = request.POST.get("amount")
        amount = decimal.Decimal(amount)
        time_left_b = listing.date + timedelta(days=7) - timezone.now()
        total_seconds_left = time_left_b.total_seconds()

        # Check if there is less than 24 hours left on the listing
        # if so, check if the user has enough funds to place the bid
        if total_seconds_left <= 86400:
            if amount > current_user.balance:
                site_account = User.objects.get(pk=12)
                subject = f"Insufficient funds for {listing.title}",
                message =f"Your bid of {amount} on {listing.title} has been cancelled due to insufficient funds. Please add funds to your account then try placing your bid again."
                contrib_messages.add_message(request, contrib_messages.ERROR, f"Your bid of {amount} on {listing.title} has been cancelled due to insufficient funds. Please add funds to your account to continue bidding.")
                send_message(site_account, current_user, subject, message)
            else:
                success, updated_listing = helpers.place_bid(request, amount, listing_id)
                if success:
                    listing = updated_listing
        else:
            success, updated_listing = helpers.place_bid(request, amount, listing_id)      
            if success:
                listing = updated_listing 
    
    
    # Get values to pass to template
    winner, user_bid, difference, watchlist_item = helpers.get_listing_values(request, listing)
    messages = contrib_messages.get_messages(request)
    comments = Comment.objects.filter(listing=listing)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()
     
    return render(request, "auctions/listing.html", {
        "listing": listing,
        "winner": winner,
        "comments": comments,
        "comment_form": CommentForm(),
        "time_left": time_left,
        "user_bid": user_bid,
        "difference": difference,
        "watchlist_item": watchlist_item,
        "current_user" : request.user,
        "unread_message_count": unread_message_count,
        "messages": messages
    })




# VIEWS - LOGIN REQUIRED
@login_required
def create(request):
    if request.method == "POST":
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.user = request.user
            listing.starting_bid = listing.price
            listing.closing_date = listing.date + timedelta(days=7)
            listing.save()
            form.save_m2m()
            return HttpResponseRedirect(reverse("index"))
    else:
        form = ListingForm()
        current_user = request.user
        messages = contrib_messages.get_messages(request)
        unread_messages = Message.objects.filter(recipient=current_user, read=False)
        unread_message_count = unread_messages.count()
        return render(request, "auctions/create.html", {
            "form": ListingForm(),
            "current_user": current_user,
            "messages": messages,
            "unread_message_count": unread_message_count
        })
    

@login_required
def watchlist(request):
    watchlist_items = Watchlist.objects.filter(user=request.user)
    listings = [item.listing for item in watchlist_items]
    current_user = request.user
    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()

    return render(request, "auctions/watchlist.html", {
        "listings": listings,
        "current_user": current_user,
        "messages": messages,
        "unread_message_count": unread_message_count
    })


@login_required
def profile(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    listings = Listing.objects.filter(user=user)
    watchlist = Watchlist.objects.filter(user=user)
    current_user = request.user
    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()
    user_bids = Bid.objects.filter(user=user)
    bid_info_list = []


    for bid in user_bids:
        bid_listing = bid.listing
        is_old_bid = helpers.check_if_old_bid(bid, bid_listing)
        highest_bid = Bid.objects.filter(listing=bid_listing).order_by("-amount").first()
        difference = bid.amount - highest_bid.amount
        user_bid_info = UserBidInfo(bid, is_old_bid, highest_bid, difference)
        bid_info_list.append(user_bid_info)

    bid_info_list = sorted(bid_info_list, key=lambda x: x.user_bid.date, reverse=True)

    return render(request, "auctions/profile.html", {
        "user": user,
        "listings": listings,
        "watchlist": watchlist,
        "user_info_form": UserInfoForm(instance=user),
        "current_user": current_user,
        "messages": messages,
        "unread_message_count": unread_message_count,
        "bid_info_list": bid_info_list
    })


@login_required
def transactions(request, user_id):
    '''
    View all bid and transaction history, link will only
    appear on a user's own profile page
    '''
    current_user = request.user
    if user_id != current_user.id:
        return HttpResponse("Unauthorized", status=401)
    user = User.objects.get(pk=user_id)
    sent_transactions = Transaction.objects.filter(sender=user)
    received_transactions = Transaction.objects.filter(recipient=user)
    transactions = sent_transactions | received_transactions

    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()

    user_bids = Bid.objects.filter(user=user)
    user_bids = user_bids.order_by("-date")

    active_bid_count = user_bids.filter(listing__active=True).values("listing").distinct().count()

    return render(request, "auctions/transactions.html", {
        'transactions': transactions,
        'user': user,
        'current_user': current_user,
        'messages': messages,
        'unread_message_count': unread_message_count,
        'user_bids': user_bids,
        'active_bid_count': active_bid_count
    })


@login_required
def messages(request, user_id):

    current_user = request.user

    if request.method == "POST":
        try:
            visibility = request.POST["show-hide-input"]

            if visibility == "show":
                request.session["show_read"] = True
            else:
                request.session["show_read"] = False
        except:
            visibility = "unset"

        try:
            if visibility == "show" or visibility == "hide":
                pass
            else:
                recipient_id = request.POST["recipient"]
                recipient = User.objects.get(pk=recipient_id)
                subject = request.POST["subject"]
                message = request.POST["message"]

                send_message(request.user, recipient, subject, message)
                return HttpResponseRedirect(reverse("messages", args=(user_id,)))
        except:
            contrib_messages.error(request, "Error sending message")

    if user_id !=  current_user.id:
        return HttpResponse("Unauthorized", status=401)
    
    # Dynamic Show Read Messages
    sent_messages, inbox_messages, show_read_messages = helpers.show_hide_read_messages(request)

    # Dynamic Sort Messages
    sent_messages, inbox_messages, sort_by_direction = helpers.determine_message_sort(request, sent_messages, inbox_messages)
    
    # alert-msgs
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