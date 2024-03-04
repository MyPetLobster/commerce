import decimal 
import logging
from datetime import timedelta, timezone

from django import forms
from django.contrib import messages as contrib_messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.urls import reverse
from django.forms import ModelForm
from django.utils import timezone

from . import helpers
from .models import User, Listing, Category, Bid, Comment, Watchlist, Winner, Transaction, Message
from .tasks import transfer_to_escrow, transfer_to_seller, notify_winner, send_message

logger = logging.getLogger(__name__)


# Form Models for Listings, Comments, and User Info
class ListingForm(ModelForm):
    class Meta:
        model = Listing
        fields = ['title', 'description', 'price', 'image', 'categories']
        labels = {
            'title': 'Title',
            'description': 'Description',
            'price': 'Starting Bid',
            'image': 'Image URL',
            'categories': 'Categories'
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'id': 'description'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.URLInput(attrs={'class': 'form-control'}),
            'categories': forms.CheckboxSelectMultiple(attrs={'class': 'category-checkbox'}),
        }

class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['comment', 'anonymous']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'id': 'comment'}),
            'anonymous': forms.CheckboxInput(attrs={'class': 'anon-checkbox'}),
        }

class UserInfoForm(ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        help_texts = {
            'username': None,
            'email': None,
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }




# Authentication Views
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




# Views - Public
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
    current_user = request.user
    listings = Listing.objects.all()

    if current_user.is_authenticated:
        messages = contrib_messages.get_messages(request)
        unread_messages = Message.objects.filter(recipient=current_user, read=False)
        unread_message_count = unread_messages.count()

        helpers.set_inactive(listings)

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
    winners = Winner.objects.all()
    current_user = request.user
    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()

    helpers.set_inactive(listings)

    return render(request, "auctions/listings.html", {
        "listings": listings,
        "winners": winners,
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
                contrib_messages.add_message(request, contrib_messages.ERROR, "Insufficient funds")
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






# Views - Login Required
@login_required
def create(request):
    if request.method == "POST":
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.user = request.user
            listing.starting_bid = listing.price
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
    winners = Winner.objects.filter(listing__in=listings)
    current_user = request.user
    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()

    return render(request, "auctions/watchlist.html", {
        "listings": listings,
        "winners": winners,
        "current_user": current_user,
        "messages": messages,
        "unread_message_count": unread_message_count
    })

# Profile related classes and functions
class UserBidInfo:
    def __init__(self, user_bid, is_old_bid):
        self.user_bid = user_bid
        self.highest_bid = user_bid.listing.price
        self.difference = self.highest_bid - user_bid.amount
        self.is_old_bid = is_old_bid





@login_required
def profile(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    listings = Listing.objects.filter(user=user)
    watchlist = Watchlist.objects.filter(user=user)
    winners = Winner.objects.filter(listing__user=user)
    current_user = request.user
    messages = contrib_messages.get_messages(request)
    unread_messages = Message.objects.filter(recipient=current_user, read=False)
    unread_message_count = unread_messages.count()
    user_bids = Bid.objects.filter(user=user)
    bid_info_list = []

    for bid in user_bids:
        bid_listing = bid.listing
        is_old_bid = helpers.check_if_old_bid(bid, bid_listing)

        user_bid_info = UserBidInfo(bid, is_old_bid)


        bid_info_list.append(user_bid_info)

    bid_info_list = sorted(bid_info_list, key=lambda x: x.user_bid.date, reverse=True)


    return render(request, "auctions/profile.html", {
        "user": user,
        "listings": listings,
        "watchlist": watchlist,
        "winners": winners,
        "user_info_form": UserInfoForm(instance=user),
        "current_user": current_user,
        "messages": messages,
        "unread_message_count": unread_message_count,
        "bid_info_list": bid_info_list
    })




# ACTION VIEWS


    

    

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
        if highest_bid.amount > starting_bid:
            winner = Winner.objects.create(
                amount=listing.price,
                listing=listing,
                user=highest_bid.user
            )
            winner.save()
            notify_winner(winner, listing)
            transfer_to_escrow(winner)
        else:
            listing.cancelled = True
        listing.active = False
        listing.save()
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
    comment.save()
    return HttpResponseRedirect(reverse("listing", args=(listing_id,)))


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
        winners = Winner.objects.all()
        return render(request, "auctions/listings.html", {
            "listings": listings,
            "winners": winners,
            "current_user": current_user,
            "messages": messages,
            "unread_message_count": unread_message_count
        })
    

# Money Related Functions
@login_required
def deposit(request, user_id):
    fake_bank_account = User.objects.get(pk=13)
    user = User.objects.get(pk=user_id)
    amount = request.POST["amount"]
    amount = decimal.Decimal(amount)
    if amount <= 0:
        contrib_messages.error(request, "Deposit amount must be greater than 0")
        return redirect("profile", user_id=user_id)
    
    transaction = Transaction.objects.create(
        amount=amount,
        sender=fake_bank_account,
        recipient=user
    )
    transaction.save()

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
    
    transaction = Transaction.objects.create(
        amount=amount,
        sender=user,
        recipient=fake_bank_account
    )
    transaction.save()

    fake_bank_account.balance += amount
    fake_bank_account.save()
    user.balance -= amount
    user.save()
    return redirect("profile", user_id=user_id)


# Seller will have a button on profile to confirm shipping.
# Once pressed, money will be transferred from escrow to seller.
@login_required
def confirm_shipping(listing_id):
    listing = Listing.objects.get(pk=listing_id)
    if listing.shipped == False:
        if transfer_to_seller(listing_id):
            listing.shipped = True
            listing.save()    
    
    return redirect("listing", listing_id=listing_id)


# View all transaction and bid history. Can only view own transactions.
@login_required
def transactions(request, user_id):
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

    active_bid_count = user_bids.filter(listing__active=True).count()

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


def delete_message(request, message_id):
    current_user = request.user
    message = Message.objects.get(pk=message_id)
    message.deleted_by.add(current_user)
    message.save()
    return HttpResponseRedirect(reverse("messages", args=(request.user.id,)))


def mark_all_as_read(request, user_id):
    messages = Message.objects.filter(recipient=request.user)
    for message in messages:
        message.read = True
        message.save()
    return HttpResponseRedirect(reverse("messages", args=(user_id,)))











