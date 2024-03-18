from celery import shared_task
from django.utils import timezone

from collections import defaultdict
from datetime import timedelta
import logging

from . import auto_messages as a_msg
from . import helpers
from .models import Bid, Listing, User, Transaction


logger = logging.getLogger(__name__)




# Periodic Tasks
# Used in - views.index, celery.py
@shared_task
def set_inactive():
    '''
    This task checks if the closing date for a listing has passed. If it has, the listing is set to 
    inactive and the winner is declared. Includes safety check to ensure closing_date is not None, 
    should be set on creation of listing. Calls declare_winner helper function to handle all the
    logic for handing the closing of a listing.

    Frequency: Every 60 seconds

    Args: None
    Returns: None

    Called by: views.index
    '''

    listings = Listing.objects.filter(active=True)
    for listing in listings:
        if listing.closing_date == None:
            listing.closing_date = listing.date + timedelta(days=7)
            listing.save()
        if listing.closing_date < timezone.now():
            listing.active = False
            listing.save()
            helpers.declare_winner(listing)
        else:
            pass


@shared_task
def check_user_fees():
    '''
        This tasks checks to see if any users have a fee_failure_date that is older than 7 days. 
        If they do, they are charged 5% on the outstanding balance for each day that the fee is overdue.

        If the user has a negative balance after 28 days, the user is notified of imminent account closure
        and legal action.

        If the user has a negative balance after 30 days, the account is closed and negative balance paid 
        by legal department.

        Frequency: Every 12 hours

        Args: None
        Returns: None

        Called by: views.index
    '''

    users_with__late_fees = User.objects.filter(fee_failure_date__lt=timezone.now() - timedelta(days=7))
    site_account = User.objects.get(pk=12)
    for user in users_with__late_fees:
        # Failsafe, should be handled by actions.deposit
        if user.balance > 0:
            user.fee_failure_date = None
            user.save()

            # send error message to admin
            admin = User.objects.get(pk=2)
            subject = "FEE FAILURE CONFLICT"
            message = f"""User {user.username} has a positive balance but a fee_failure_date. Please investigate. 
                        Source - tasks.check_user_fees()"""
            a_msg.send_message(admin, user, subject, message)
            continue

        days_overdue = (timezone.now() - user.fee_failure_date).days if user.fee_failure_date else 0
        
        if days_overdue > 7:
            user.balance = user.balance + (user.balance * 0.05) * (days_overdue - 7)
            user.save()
        
        if user.balance < 0 and days_overdue > 28 and days_overdue <= 30:
            a_msg.send_account_closure_message(user.id)

        if user.balance < 0 and days_overdue > 30:
            user.username = f"inactive_{user.username}"
            user.set_password(User.objects.make_random_password())
            user.save()
            Transaction.objects.create(
                amount=user.balance * -1, 
                sender=user,
                recipient=site_account, 
                notes="legal"
            )
            user.balance = 0
            user.save()
            # TODO: Send email to user to notify them and give contact info for collections department


@shared_task
def check_if_bids_funded():
    '''
    This task checks if bids on active listings are funded. If there are less than 24 hours left before the listing closes
    and the bid is not funded, the bid is deleted and the user is notified.

    Frequency: Every 15 minutes

    Args: None
    Returns: None

    Called by: views.index
    '''
    # Retrieve all the active bids that are closing within the next 24 hours
    active_bids = Bid.objects.filter(listing__active=True,
                                      listing__closing_date__gt=timezone.now(),
                                      listing__closing_date__lt=timezone.now() + timezone.timedelta(days=1))

    # Dictionary to hold users and listings so we only message each user once for each unique listing
    # Even if we are deleting multiple bids they have placed
    messaged_users_listings = defaultdict(int)

    for bid in active_bids:
        user = bid.user
        listing = bid.listing

        # Update the listing.price to highest bid each iteration
        highest_bid = Bid.objects.filter(listing=listing).order_by('-amount').first()
        listing.price = highest_bid.amount
        listing.save()

        now = timezone.now()
        listing_closing_date = listing.closing_date

        # Get cutoff date for unfunded bids, 1 day before listing closing date if listing is not cancelled
        # If listing is cancelled, get cutoff date 1 day after listing closing date
        if listing.cancelled == False:
            cutoff_date = listing_closing_date - timezone.timedelta(days=1)
        else:
            cutoff_date = listing_closing_date + timezone.timedelta(days=1)

        # If the bid is unfunded and the listing is closing within the next 24 hours, delete the bid and notify the user
        if now > cutoff_date and user.balance < listing.price:
            bid.delete()

            next_bid = Bid.objects.filter(listing=listing).order_by('-amount').first()
            if next_bid:
                listing.price = next_bid.amount
            else:
                listing.price = listing.starting_bid

            listing.save()

            time_left = listing_closing_date - now
            hours_left = time_left.total_seconds() // 3600
            minutes_left = (time_left.total_seconds() % 3600) // 60
            time_left_str = f"{int(hours_left)} hours and {int(minutes_left)} minutes"

            if not messaged_users_listings[(user.id, listing.id)]:
                a_msg.send_bid_removed_message(user, listing, time_left_str)
                messaged_users_listings[(user.id, listing.id)] = 1
