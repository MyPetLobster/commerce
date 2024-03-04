
from django.utils import timezone
from django import template
from auctions.models import User, Bid, Listing

register = template.Library()

@register.filter
def subtract(value, arg):
    return value - arg


@register.filter
def get_user_high_bid(value, user_id,):
    user = User.objects.get(pk=user_id)
    listing = Listing.objects.get(pk=value)
    bids = Bid.objects.filter(listing=listing, user=user)
    if bids.exists():
        return f'${bids.order_by('-amount').first().amount}'
    else:
        return 'No Bids'
    

@register.filter
def get_time_left(listing_id):
    listing = Listing.objects.get(pk=listing_id)
    now = timezone.now()
    time_left = listing.date + timezone.timedelta(days=7) - now
    if time_left.days < 1:
        status = 'red'
    elif time_left.days < 2:
        status = 'yellow'
    else:
        status = 'green'
    time_left = f'{time_left.days} days, {time_left.seconds//3600} hours, {(time_left.seconds//60)%60} minutes left'
    return time_left, status