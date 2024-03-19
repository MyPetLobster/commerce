from django.utils import timezone

import random
from datetime import timedelta

from .models import Listing


# ADMIN ONLY FUNCTIONS

# Site Database Maintenance
def set_closing_dates_if_not_set():
    '''
    This view is used to set closing dates for listings that were created
    before the closing_date field was added to the Listing model. 
    '''

    listings = Listing.objects.filter(active=True)
    for listing in listings:
        if listing.closing_date == None:
            listing.closing_date = listing.date + timedelta(days=7)
            listing.save()

def force_set_closing_dates():
    '''
    This view is used to update all closing dates for all listings,
    allowing admin to modify listing date of test listings
    '''

    listings = Listing.objects.all()
    for listing in listings:
        if listing.active == True:
            listing.closing_date = listing.date + timedelta(days=7)
            listing.save()


def randomize_dates():
    '''
    This view is used to randomize the closing dates for all listings,
    allowing for testing of the website with the included sample data.
    '''

    listings = Listing.objects.all()
    now = timezone.now()

    for listing in listings:
        random_timedelta = timedelta(days=random.randint(0, 6), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        listing_date = now - random_timedelta
        listing.date = listing_date
        listing.closing_date = listing_date + timedelta(days=7)
        listing.active = True
        listing.closed = False
        listing.in_escrow = False
        listing.shipped = False
        listing.cancelled = False
        listing.save()