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