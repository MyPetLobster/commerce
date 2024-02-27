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

from .models import User, Listing, Category, Bid, Comment, Watchlist, Winner
from .tasks import send_error_notification

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
        try: 
            amount = float(request.POST["amount"])
            current_price = float(listing.price)

            if amount <= current_price:
                return render(request, "auctions/listing.html", {
                    "listing": listing,
                    "comments": comments,
                    "comment_form": CommentForm(),
                    "time_left": time_left,
                    "user_bid": user_bid,
                    "difference": difference,
                    "watchlist_item": watchlist_item,
                    "message": "Bid must be higher than current price"
                })
            else:
                bid = Bid.objects.create(
                    amount=amount,
                    listing=listing,
                    user=request.user
                )
                bid.save()
                listing.price = bid.amount
                listing.save()
                return HttpResponseRedirect(reverse("listing", args=(listing_id,)))
            
        except ValueError:
            return render(request, "auctions/listing.html", {
                "listing": listing,
                "comments": comments,
                "comment_form": CommentForm(),
                "time_left": time_left,
                "user_bid": user_bid,
                "difference": difference,
                "watchlist_item": watchlist_item,
                "message": "Error placing bid. Please try again."
            })

    # Calculate Time Left (7 days from listing date)    
    listing_date = listing.date
    current_date_time = timezone.now()
    diff_seconds = round((listing_date - current_date_time).total_seconds() * -1.0, 2)

    # If more than 7 days have passed, close the listing (celery beat task will handle this in production, see tasks.py)
    if diff_seconds > 604800:

        # In production, celery will have already closed & notified winner, so this block will be skipped
        if listing.active:
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
            except:
                pass

        # Create a string to display the date the listing was closed
        # Assign str to time_left, same variable used for time left if listing is still active
        # Logic to handle the difference is in the template JS
        closed_date = listing.date + timedelta(days=7)
        time_left = f"Listing closed on {closed_date.month}/{closed_date.day}/{closed_date.year}"

    else:
        # Generate time left string to be handled in the template JS
        seconds_left = max(0, 604800 - diff_seconds)
        days_left, seconds_left = divmod(seconds_left, 86400)
        hours_left, remainder = divmod(seconds_left, 3600)
        minutes_left, seconds_left = divmod(remainder, 60)
        seconds_left = math.floor(seconds_left)
        time_left = f"{int(days_left)} days, {int(hours_left)} hours, {int(minutes_left)} minutes, {int(seconds_left)} seconds"

    # Find the winner of the listing, if winner exists
    try:
        winner = Winner.objects.get(listing=listing)
    except Winner.DoesNotExist:
        winner = None

    # Find the user's bid on the listing, if it exists
    try:
        user_bid = Bid.objects.get(user=request.user, listing=listing)
        difference = listing.price - user_bid.amount
    except:
        user_bid = None
        difference = None

    # Check if the listing is on the user's watchlist
    try:
        watchlist_item = Watchlist.objects.get(user=request.user, listing=listing)
    except Watchlist.DoesNotExist:
        watchlist_item = "not on watchlist"

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "winner": winner,
        "comments": comments,
        "comment_form": CommentForm(),
        "time_left": time_left,
        "user_bid": user_bid,
        "difference": difference,
        "watchlist_item": watchlist_item
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
        title = request.POST["title"]
        description = request.POST["description"]
        price = request.POST["price"]
        image = request.POST["image"]
        category_ids = request.POST.getlist("categories")  

        listing = Listing.objects.create(
            title=title,
            description=description,
            starting_bid=price,
            price=price,
            image=image,
            user=request.user
        )

        listing.categories.set(category_ids)

        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/create.html", {
            "form": ListingForm()
        })
    

@login_required
def watchlist(request):
    watchlist_items = Watchlist.objects.filter(user=request.user)
    listings = [item.listing for item in watchlist_items]
    winners = Winner.objects.filter(user=request.user)

    return render(request, "auctions/watchlist.html", {
        "listings": listings,
        "winners": winners
    })


@login_required
def profile(request, user_id):
    user = User.objects.get(pk=user_id)
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
    try:
        highest_bid = Bid.objects.filter(listing=listing).order_by("-amount").first()
        winner = Winner.objects.create(
            amount=listing.price,
            listing=listing,
            user=highest_bid.user
        )
        winner.save()
    except:
        pass
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
    