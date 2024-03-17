from django.contrib import messages as contrib_messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, models
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.urls import reverse
from django.utils import timezone

import decimal 
import logging
from datetime import timedelta

# Uncomment the following line to use the maintenance functions
# from . import maintenance

from .auto_messages import send_message
from . import helpers
from . import tasks
from .models import Bid, Category, Comment, Listing, Message, Transaction, User, Watchlist
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




# VIEWS - PUBLIC
def index(request):
    '''
    Render the index/active listings page. 

    Args:
        request (HttpRequest): The request object
    Returns:
        HttpResponse: The index template

    Function Calls: check_if_bids_funded(), tasks.set_inactive()
    Optional Function Calls: maintenance.force_set_closing_dates()
    '''

    # Uncomment the following lines to use the maintenance functions
    # maintenance.force_set_closing_dates()
    
    # Celery periodic task here for now
    # tasks.check_if_bids_funded()
    # tasks.set_inactive()
    # tasks.check_user_fees()

    current_user = request.user
    listings = Listing.objects.all().order_by("-date")

    if current_user.is_authenticated:
        unread_message_count = Message.objects.filter(recipient=current_user, read=False).count()

    return render(request, "auctions/index.html" , {
        "listings": listings,
        "current_user": current_user,
        "messages": contrib_messages.get_messages(request) if current_user.is_authenticated else None,
        "unread_message_count": unread_message_count if current_user.is_authenticated else None
    })


def listing(request, listing_id):
    '''
    Render the listing page and handle POST requests for placing bids and adding comments

    Args:
        request (HttpRequest): The request object
        listing_id (int): The id of the listing to view
    Returns:
        HttpResponse: The listing template

    Function Calls: check_valid_bid(), get_listing_values(), calculate_time_left()
    '''
    listing = get_object_or_404(Listing, pk=listing_id)
    current_user = request.user

    # POST Request - Place Bid
    if request.method == "POST":
        amount = decimal.Decimal(request.POST.get("amount"))

        # begin bid validation (see helpers.py to follow), get updated listing object
        listing = helpers.check_valid_bid(request, listing.id, amount)

    # Get values to pass to template
    winner, user_bid, difference, watchlist_item = helpers.get_listing_values(request, listing)
    messages = contrib_messages.get_messages(request)
    comments = Comment.objects.filter(listing=listing)
    if current_user.is_authenticated:
        unread_message_count = Message.objects.filter(recipient=current_user, read=False).count()
    time_left = helpers.calculate_time_left(listing_id)

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "winner": winner,
        "comments": comments,
        "comment_form": CommentForm() if current_user.is_authenticated else None,
        "time_left": time_left,
        "user_bid": user_bid if current_user.is_authenticated else None,
        "difference": difference if user_bid else None,
        "watchlist_item": watchlist_item if current_user.is_authenticated else None,
        "current_user" : request.user,
        "unread_message_count": unread_message_count if current_user.is_authenticated else None,
        "messages": messages
    })


def categories(request):
    categories = get_list_or_404(Category.objects.all())
    current_user = request.user

    if current_user.is_authenticated:
        unread_message_count = Message.objects.filter(recipient=current_user, read=False).count()

    return render(request, "auctions/categories.html", {
        "categories": categories,
        "current_user": current_user,
        "messages": contrib_messages.get_messages(request) if current_user.is_authenticated else None,
        "unread_message_count": unread_message_count if current_user.is_authenticated else None
    })


def category(request, category_id):
    listings = get_list_or_404(Listing.objects.filter(categories=category_id))
    category = get_object_or_404(Category, pk=category_id)
    current_user = request.user

    if current_user.is_authenticated:
        unread_message_count = Message.objects.filter(recipient=current_user, read=False).count()

    return render(request, "auctions/category.html", {
        "listings": listings,
        "category": category,
        "current_user": current_user,
        "messages": contrib_messages.get_messages(request) if current_user.is_authenticated else None,
        "unread_message_count": unread_message_count if current_user.is_authenticated else None
    })


def search(request):
    current_user = request.user
    post = False

    if request.method == "POST":
        post = True
        search_query = request.POST["search-query"]
        listings = Listing.objects.filter(title__icontains=search_query).filter(active=True).order_by("-date")
    
    return render(request, "auctions/search.html", {
        "listings": listings if post else None,
        "current_user": current_user,
        "messages": contrib_messages.get_messages(request),
        "unread_message_count": Message.objects.filter(recipient=current_user, read=False).count()
    })


def about(request):
    if request.user.is_authenticated:
        current_user = request.user
        return render(request, "auctions/about.html", {
            "current_user": current_user,
            "messages": contrib_messages.get_messages(request),
            "unread_message_count": Message.objects.filter(recipient=current_user, read=False).count()
        })
    else:
        return render(request, "auctions/about.html")




# VIEWS - LOGIN REQUIRED
@login_required
def listings(request):
    current_user = request.user
    return render(request, "auctions/listings.html", {
        "listings": Listing.objects.all().order_by("-date"),
        "current_user": current_user,
        "messages": contrib_messages.get_messages(request),
        "unread_message_count": Message.objects.filter(recipient=current_user, read=False).count()
    })


@login_required
def profile(request, user_id):
    '''
    Render the user's profile page and handle POST requests for updating user info

    Args:
        request (HttpRequest): The request object
        user_id (int): The user id of the user to view
    Returns:
        HttpResponse: The user's profile page

    Function Calls: create_bid_info_object_list()
    '''
    user = get_object_or_404(User, pk=user_id)
    listings = Listing.objects.filter(user=user).order_by("-date")
    current_user = request.user

    # Create a list of bid info objects (see classes.py for BidInfo class definition)
    user_active_bids = Bid.objects.filter(user=user, listing__active=True)
    bid_info_list = helpers.create_bid_info_object_list(user_active_bids)
    return render(request, "auctions/profile.html", {
        "user": user,
        "current_user": current_user,
        "listings": listings,
        "watchlist": Watchlist.objects.filter(user=user),
        "user_info_form": UserInfoForm(instance=user),
        "messages": contrib_messages.get_messages(request),
        "unread_message_count": Message.objects.filter(recipient=current_user, read=False).count(),
        "bid_info_list": bid_info_list,
        "user_active_listings_count": Listing.objects.filter(user=user, active=True).count(),
        "user_inactive_listings_count": Listing.objects.filter(user=user, active=False).count(),
        "user_active_bids_count": Bid.objects.filter(user=user, listing__active=True).count()
    })


@login_required
def create(request):
    '''
    Render the create listing form and handle POST requests for creating a new listing

    Args:
        request (HttpRequest): The request object
    Returns:
        HttpResponse: The create listing form template

    Function Calls: None
    '''
    current_user = request.user
    if request.method == "POST":
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.user = request.user
            listing.starting_bid = listing.price
            listing.closing_date = timezone.now() + timedelta(days=7)
            listing.save()
            form.save_m2m()
            return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/create.html", {
            "form": ListingForm(),
            "current_user": current_user,
            "messages": contrib_messages.get_messages(request),
            "unread_message_count": Message.objects.filter(recipient=current_user, read=False).count()
        })
    

@login_required
def messages(request, user_id):
    '''
    Render messages template and handle POST requests for sending messages and the 
    option to show/hide read messages. If user calls actions.sort_messages(), the
    environment variable set by that action will be used here to sort the messages
    on page load.
    
    Args:
        user_id (int): The user id of the recipient of the message
    Returns:
        HttpResponse: The messages template
    
    Function Calls: show_hide_read_messages(), set_message_sort(), send_message()
'''
    current_user = request.user

    # Check if user is authorized to view messages
    if user_id !=  current_user.id:
        return HttpResponse("Unauthorized", status=401)
    
    # There are two types of POST requests: show/hide read messages and send message
    if request.method == "POST":
        # Show/Hide Read Messages
        visibility = request.POST.get("show-hide-input", "unset")
        if visibility == "show":
            request.session["show_read"] = True
        else:
            request.session["show_read"] = False

        # Send Message if not a show/hide request
        if visibility == "unset":
            recipient_id = request.POST["recipient"]
            recipient = User.objects.get(pk=recipient_id)
            subject = request.POST["subject"]
            message = request.POST["message"]
            send_message(request.user, recipient, subject, message)
            return HttpResponseRedirect(reverse("messages", args=(user_id,)))

    # Get messages filtered by show/hide read messages
    sent_messages, inbox_messages, show_read_messages = helpers.show_hide_read_messages(request)
    # Sort messages by user preference, newest first is default
    sort_by_direction = request.POST.get("sort_by_direction", "newest-first")
    sent_messages, inbox_messages, sort_by_direction = helpers.set_message_sort(request, sent_messages, inbox_messages)

    return render(request, "auctions/messages.html", {
        'sent_messages': sent_messages,
        'inbox_messages': inbox_messages,
        'inbox_count': len(inbox_messages),
        'show_read_messages': show_read_messages,
        'sort_by_direction': sort_by_direction,
        'current_user': current_user,
        'messages': contrib_messages.get_messages(request),
        'unread_message_count': Message.objects.filter(recipient=current_user, read=False).count()
    })


@login_required
def transactions(request, user_id):
    '''
    View all bid and transaction history, link will only
    appear on a user's own profile page.

    Args:
        user_id (int): The user id of the user to view
    Returns:
        HttpResponse: The transactions template

    Function Calls: None
    '''
    current_user = request.user
    user = get_object_or_404(User, pk=user_id)
    if user != current_user:
        return HttpResponse("Unauthorized", status=401)
    
    # Fetch transactions
    transactions = Transaction.objects.filter(models.Q(sender=user) | models.Q(recipient=user))
    transactions = transactions.order_by("-date")

    user_bids = Bid.objects.filter(user=user)
    user_bids_by_date = sorted(user_bids, key=lambda x: x.date, reverse=True)

    # Group bids by the listing, groups are sorted by date of the most recent bid
    # Then turn back into a list of bids while retaining the order of the groups
    bid_listing_groups = {}
    for bid in user_bids_by_date:
        if bid.listing.id in bid_listing_groups:
            bid_listing_groups[bid.listing.id].append(bid)
        else:
            bid_listing_groups[bid.listing.id] = [bid]

    # Create list of bids grouped by listing and sorted by date
    user_bids = []
    for key, value in bid_listing_groups.items():
        user_bids.extend(value)

    active_bid_count = Bid.objects.filter(user=user, listing__active=True).count()

    return render(request, "auctions/transactions.html", {
        'user': user,
        'current_user': current_user,
        'transactions': transactions,
        'messages': contrib_messages.get_messages(request),
        'unread_message_count': Message.objects.filter(recipient=current_user, read=False).count(),
        'user_bids': user_bids,
        'active_bid_count': active_bid_count
    })


@login_required
def watchlist(request):
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