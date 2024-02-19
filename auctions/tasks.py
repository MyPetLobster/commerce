from celery import shared_task
from datetime import timezone, utcnow
from .models import User, Listing, Winner, Bid, Comment, Watchlist

@shared_task()
def check_for_inactive_listings():
    listings = Listing.objects.filter(active=True)
    
    for listing in listings:
        listing_date_time = (listing.date).astimezone(timezone.utc)
        current_date_time = utcnow()

        diff_seconds = round((listing_date_time - current_date_time).total_seconds() * -1.0, 2)

        if diff_seconds < 0:
            if listing.active:
                listing.active = False
                listing.save()
                try:
                    winner = Winner.objects.get(listing=listing)
                except Winner.DoesNotExist:
                    winner = None
                if winner is None:
                    bids = Bid.objects.filter(listing=listing)
                    if bids:
                        winner = Winner.objects.create(
                            user=bids[0].user,
                            listing=listing
                        )
                        winner.save()

