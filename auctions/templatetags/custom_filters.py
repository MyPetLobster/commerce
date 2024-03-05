
from django.utils import timezone
from django import template
from auctions.models import User, Bid, Listing

register = template.Library()

@register.filter
def subtract(value, arg):
    difference = value - arg
    return f"${difference:,.2f}"


@register.filter
def get_user_high_bid(value, user_id,):
    user = User.objects.get(pk=user_id)
    listing = Listing.objects.get(pk=value)
    bids = Bid.objects.filter(listing=listing, user=user)
    if bids.exists():
        high_bid = bids.order_by('-amount').first().amount
        return f"${high_bid:,.2f}"
    else:
        return 'No Bids'
    

@register.filter
def get_time_left(listing_id):
    listing = Listing.objects.get(pk=listing_id)
    now = timezone.now()
    time_left = listing.date + timezone.timedelta(days=7) - now
    if time_left.days < 1:
        if time_left.seconds < 43200:
            status = 'red'
        else:
            status = 'orange'
    elif time_left.days < 2:
        status = 'yellow'
    else:
        status = 'green'
    if time_left.days < 0:
        time_left = 'Auction Ended'
    elif time_left.days == 0:
        time_left = f'{time_left.seconds//3600} hours, {(time_left.seconds//60)%60} minutes left'
    else:
        time_left = f'{time_left.days} days, {time_left.seconds//3600} hours, {(time_left.seconds//60)%60} minutes left'
    return time_left, status


@register.filter
def format_currency(value):
    return f"${value:,.2f}"