from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.forms import ModelForm

from .models import User, Listing, Category, Bid, Comment, Watchlist, Winner


class ListingForm(ModelForm):
    class Meta:
        model = Listing
        fields = ['title', 'description', 'price', 'image', 'categories']


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['comment', 'anonymous']


def index(request):
    listings = Listing.objects.all()

    return render(request, "auctions/index.html" , {
        "listings": listings
    })


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
    

def listing(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    comments = Comment.objects.filter(listing=listing)

    try:
        winner = Winner.objects.get(listing=listing)
    except Winner.DoesNotExist:
        winner = None

    if request.method == "POST":
        amount = request.POST["amount"]
        bid = Bid.objects.create(
            amount=amount,
            listing=listing,
            user=request.user
        )
        bid.save()
        listing.price = bid.amount
        listing.save()
        return HttpResponseRedirect(reverse("listing", args=(listing_id,)))

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "winner": winner,
        "comments": comments,
        "comment_form": CommentForm()
    })


def watchlist(request):
    watchlist_items = Watchlist.objects.filter(user=request.user)
    listings = [item.listing for item in watchlist_items]
    winners = Winner.objects.filter(user=request.user)

    return render(request, "auctions/watchlist.html", {
        "listings": listings,
        "winners": winners
    })


def add_to_watchlist(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    watchlist_item, created = Watchlist.objects.get_or_create(user=request.user, listing=listing)
    if created:
        return HttpResponseRedirect(reverse("watchlist"))
    else:
        pass
    listings = Listing.objects.all()
    return render(request, "auctions/index.html" , {
        "listings": listings
    })


def remove_from_watchlist(request, listing_id):
    if request.method == "POST":
        watchlist_item = Watchlist.objects.get(user=request.user, listing_id=listing_id)
        watchlist_item.delete()
        return HttpResponseRedirect(reverse("watchlist"))
    

def close_listing(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    highest_bid = Bid.objects.filter(listing=listing).order_by("-amount").first()
    winner = Winner.objects.create(
        amount=listing.price,
        listing=listing,
        user=highest_bid.user
    )
    winner.save()
    listing.active = False
    listing.save()
    return HttpResponseRedirect(reverse("index"))


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
