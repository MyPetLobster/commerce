from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.forms import ModelForm

from .models import User, Listing, Category, Bid, Comment, Watchlist, Winner


class ListingForm(ModelForm):
    class Meta:
        model = Listing
        fields = ['title', 'description', 'price', 'image', 'categories']


def index(request):
    listings = Listing.objects.all()

    return render(request, "auctions/index.html" , {
        "listings": listings
    })


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
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

        # Attempt to create new user
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
        category_ids = request.POST.getlist("categories")  # Assuming categories are submitted as a list of IDs

        # Create the listing object
        listing = Listing.objects.create(
            title=title,
            description=description,
            price=price,
            image=image,
            user=request.user
        )

        # Add categories to the listing using the set() method
        listing.categories.set(category_ids)

        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/create.html", {
            "form": ListingForm()
        })
    