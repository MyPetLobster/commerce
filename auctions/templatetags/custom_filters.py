
from django.utils import timezone
from django import template
from auctions.models import User, Bid, Listing

register = template.Library()

@register.filter
def subtract(value, arg):
    '''
    Subtracts arg from value and returns the result

    Used in - transactions.html 
    '''
    difference = value - arg
    return f"${difference:,.2f}"


@register.filter
def get_user_high_bid(value, user_id,):
    '''
    Returns the highest bid by the user on the listing, formatted as currency

    Used in - watchlist.html
    '''
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
    '''
    Returns the time left for the listing to close and the status of the time left
    which is used to change the color of the time left text dynamically.

    Used in - index.html, listings.html, profile.html, watchlist.html
    '''
    listing = Listing.objects.get(pk=listing_id)
    now = timezone.now()
    time_left = listing.closing_date - now
    if time_left.days < 1:
        if time_left.seconds < 43200:
            status = 'red'
        else:
            status = 'orange'
    elif time_left.days < 2:
        status = 'yellow'
    else:
        status = ''
    if time_left.days < 0:
        time_left = 'Auction Ended'
    elif time_left.days == 0:
        time_left = f'{time_left.seconds//3600} hours, {(time_left.seconds//60)%60} minutes left'
    else:
        time_left = f'{time_left.days} days, {time_left.seconds//3600} hours, {(time_left.seconds//60)%60} minutes left'
    return time_left, status


@register.filter
def format_currency(value):
    '''
    Formats the value as currency

    Used in -   category.html, index.html, layout.html, listing.html, listings.html, profile.html, 
                transactions.html, watchlist.html
    '''

    return f"${value:,.2f}"