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


