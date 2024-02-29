import decimal 
import logging
import math
from datetime import timedelta, timezone

from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.urls import reverse
from django.forms import ModelForm
from django.utils import timezone

from .models import User, Listing, Category, Bid, Comment, Watchlist, Winner, Transaction, Message
from .tasks import send_error_notification, transfer_to_escrow, transfer_to_seller, notify_winner, send_message, check_bids_funds

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
def index(request):
    listings = Listing.objects.all()

    if not listings:
        logger.error("No listings found")
        send_error_notification("No listings found")
        return render(request, "auctions/index.html", {
            "message": "No listings found"
        })

    return render(request, "auctions/index.html" , {
        "listings": listings
    })


def listings(request):
    listings = get_list_or_404(Listing.objects.all())
    winners = Winner.objects.all()

    return render(request, "auctions/listings.html", {
        "listings": listings,
        "winners": winners
    })


def listing(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    comments = Comment.objects.filter(listing=listing)

    # Place Bid
    if request.method == "POST":
        amount = request.POST.get("amount")
        time_left = listing.date + timedelta(days=7) - timezone.now()
        total_seconds_left = time_left.total_seconds()
        if total_seconds_left <= 86400:
            user_balance = request.user.balance
            if amount > user_balance:
                messages.error(request, "Insufficient funds. Must have enough deposited to cover a bid within 24 hours of listing expiration.")
                return HttpResponseRedirect(reverse("listing", args=(listing_id,)))
            
        if place_bid(request, amount, listing_id):
            return HttpResponseRedirect(reverse("listing", args=(listing_id,)))
        else:
            messages.error(request, "Failed to place bid. Please try again.")

    # Calculate Time Left (7 days from listing date)    
    listing_date = listing.date
    current_date_time = timezone.now()
    diff_seconds = round((listing_date - current_date_time).total_seconds() * -1.0, 2)

    # In production, celery will have already closed listings & notified winners
    if check_expiration(listing_id) == "closed - expired":
        closed_date = listing.date + timedelta(days=7)
        time_left = f"Listing expired on {closed_date.month}/{closed_date.day}/{closed_date.year}"
    elif check_expiration(listing_id) == "closed - by seller":
        time_left = "Listing closed by seller"
    else:
        # Generate time left string to be handled in the template JS
        seconds_left = max(0, 604800 - diff_seconds)
        days_left, seconds_left = divmod(seconds_left, 86400)
        hours_left, remainder = divmod(seconds_left, 3600)
        minutes_left, seconds_left = divmod(remainder, 60)
        seconds_left = math.floor(seconds_left)
        time_left = f"{int(days_left)} days, {int(hours_left)} hours, {int(minutes_left)} minutes, {int(seconds_left)} seconds"

    # Get values to pass to template
    try:
        winner = Winner.objects.get(listing=listing)
    except Winner.DoesNotExist:
        winner = None

    try:
        user_bid = Bid.objects.get(user=request.user, listing=listing)
        difference = listing.price - user_bid.amount
    except:
        user_bid = None
        difference = None
    try:
        watchlist_item = Watchlist.objects.filter(user=request.user, listing=listing)
    except:
        watchlist_item = None

    if watchlist_item != None:
        pass
    else:
        watchlist_item = "not on watchlist"
    
    return render(request, "auctions/listing.html", {
        "listing": listing,
        "winner": winner,
        "comments": comments,
        "comment_form": CommentForm(),
        "time_left": time_left,
        "user_bid": user_bid,
        "difference": difference,
        "watchlist_item": watchlist_item,
        "user" : request.user
    })


def categories(request):
    categories = get_list_or_404(Category.objects.all())

    return render(request, "auctions/categories.html", {
        "categories": categories
    })


def category(request, category_id):
    listings = Listing.objects.filter(categories=category_id)
    category = get_object_or_404(Category, pk=category_id)

    return render(request, "auctions/category.html", {
        "listings": listings,
        "category": category
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
        return render(request, "auctions/create.html", {
            "form": ListingForm()
        })
    

@login_required
def watchlist(request):
    watchlist_items = Watchlist.objects.filter(user=request.user)
    listings = [item.listing for item in watchlist_items]
    winners = Winner.objects.filter(listing__in=listings)

    return render(request, "auctions/watchlist.html", {
        "listings": listings,
        "winners": winners
    })


@login_required
def profile(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    listings = Listing.objects.filter(user=user)
    watchlist = Watchlist.objects.filter(user=user)
    winners = Winner.objects.filter(listing__user=user)
    current_user = request.user

    return render(request, "auctions/profile.html", {
        "user": user,
        "listings": listings,
        "watchlist": watchlist,
        "winners": winners,
        "user_info_form": UserInfoForm(instance=user),
        "current_user": current_user
    })




# Functions and Actions
def check_expiration(listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    if listing.active:
        now = timezone.now()
        if listing.date + timedelta(days=7) < now:
            listing.active = False
            listing.save()
            try:
                highest_bid = Bid.objects.filter(listing=listing).order_by("-amount").first()
                winner = Winner.objects.create(
                    amount=listing.price,
                    listing=listing,
                    user=highest_bid.user
                )
                winner.save()
                notify_winner(winner, listing)
                transfer_to_escrow(winner)
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


@login_required
def place_bid(request, amount, listing_id):
    try: 
        listing = Listing.objects.get(pk=listing_id)
        amount = decimal(amount)
        current_price = decimal(listing.price)

        if amount <= current_price:
            return False
        else:
            bid = Bid.objects.create(
                amount=amount,
                listing=listing,
                user=request.user
            )
            listing.price = bid.amount
            listing.save()
            
            admin = User.objects.get(pk=2)
            bidder = request.user
            subject = f"New bid on {listing.title}"
            message = f"{request.user.username} placed a bid of ${amount} on {listing.title}. Good luck!"
            send_message(admin, bidder, subject, message)

            check_bids_funds(listing_id)

            return True
        
    except (Listing.DoesNotExist, ValueError, IntegrityError) as e:
        logger.error(f"Error placing bid: {e}")
        return False
    

@login_required
def add_to_watchlist(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    watchlist_item, created = Watchlist.objects.get_or_create(user=request.user, listing=listing)
    if created:
        return HttpResponseRedirect(reverse("listing", args=(listing_id,)))
    else:
        pass
    listings = Listing.objects.all()
    return render(request, "auctions/index.html" , {
        "listings": listings
    })


@login_required
def remove_from_watchlist(request, listing_id):
    if request.method == "POST":
        watchlist_item = Watchlist.objects.get(user=request.user, listing_id=listing_id)
        watchlist_item.delete()
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
        messages.error(request, "Old password is incorrect")
        return redirect("profile", user_id=user_id)

    if new_password != new_password_confirm:
        messages.error(request, "Passwords do not match")
        return redirect("profile", user_id=user_id)
    
    user.set_password(new_password)
    user.save()
    
    messages.success(request, "Password changed successfully")
    return redirect("profile", user_id=user_id)


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
        

    if page == "index":
        return render(request, "auctions/index.html", {
            "listings": listings
        })
    elif page == "listings":
        winners = Winner.objects.all()
        return render(request, "auctions/listings.html", {
            "listings": listings,
            "winners": winners
        })
    

# Money Related Functions
@login_required
def deposit(request, user_id):
    fake_bank_account = User.objects.get(pk=13)
    user = User.objects.get(pk=user_id)
    amount = request.POST["amount"]
    amount = decimal.Decimal(amount)
    if amount <= 0:
        messages.error(request, "Deposit amount must be greater than 0")
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
        messages.error(request, "Withdrawal amount must be greater than 0")
        return redirect("profile", user_id=user_id)
    if amount > user.balance:
        messages.error(request, "Insufficient funds")
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


@login_required
def confirm_shipping(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    if listing.shipped == False:
        if transfer_to_seller(listing_id):
            listing.shipped = True
            listing.save()    
    
    return redirect("listing", listing_id=listing_id)


@login_required
def transactions(request, user_id):
    if user_id != request.user.id:
        return HttpResponse("Unauthorized", status=401)
    user = User.objects.get(pk=user_id)
    sent_transactions = Transaction.objects.filter(sender=user)
    received_transactions = Transaction.objects.filter(recipient=user)
    transactions = sent_transactions | received_transactions

    return render(request, "auctions/transactions.html", {
        'transactions': transactions,
        'user': user
    })


@login_required
def messages(request, user_id):
    if user_id != request.user.id:
        return HttpResponse("Unauthorized", status=401)
    user = User.objects.get(pk=user_id)
    sent_messages = Message.objects.filter(sender=user)
    received_messages = Message.objects.filter(recipient=user)
    messages = sent_messages | received_messages

    return render(request, "auctions/messages.html", {
        'messages': messages,
        'user': user
    })