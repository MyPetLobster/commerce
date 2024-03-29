# Yard Sale - CS50W - Project 2 Commerce
### By Cory Suzuki - March 2024

This project was developed to satisfy the requirements for CS50W Project 2 Commerce. 

Yard Sale is a Django web application that allows users to create auction listings, place bids, comment on listings, and interact with other users through messaging. In addition to meeting the project requirements, Yard Sale includes several advanced features and enhancements.


## Youtube Video Demonstration

**Submission Video (5 minutes)**

<a href="https://www.youtube.com/watch?v=RC2Ha8ITHW0"><img src="https://img.youtube.com/vi/RC2Ha8ITHW0/0.jpg" height="150px"></a>

**Director's Cut (12 minutes)**

<a href="https://youtu.be/zFdEkO3UKGk"><img src="https://img.youtube.com/vi/zFdEkO3UKGk/0.jpg" height="150px"></a>



## Imgur Albums
**Site Screenshots**

<a href="https://imgur.com/a/CFxwKk6"><img src="https://i.imgur.com/a3b1qYO.jpeg" height="275px"></a>

**Profile Pictures - generated by DeepAI except my own, the Helldivers guy, and Terry Rozier**
- https://imgur.com/a/Mig4UvS

**Listings - most images generated by DeepAI** 
- https://imgur.com/a/vL3LpWp




## Project Requirements

### Models
- Yard Sale includes models for auction listings, bids, comments, and users.
- Additional models include categories, messages, transactions, and watchlists.

### Create Listing
- Users can create new auction listings with titles, descriptions, starting bids, and optional image URLs and categories.

### Active Listings Page
- The default route displays all active auction listings with relevant details.

### Listing Page
- Clicking on a listing displays detailed information, including the current price.
- Signed-in users can add the item to their watchlist or place bids.
- Sellers can close auctions, declaring the highest bidder as the winner.
- Users can add comments to the listing page, which are color-coded based on the commenter.

### Watchlist
- Users can view all listings they've added to their watchlist.

### Categories
- Users can view listings by category.

### Django Admin Interface
- Site administrators have full CRUD functionality for listings, comments, and bids.

## Additional Features

1. **About Page with FAQ**
   - Users can view a list of FAQs, with answers revealed on click and a link to terms and conditions.

2. **Messaging System**
   - Full messaging functionality for users, including sent/received messages, and sorting options. 
   - Messages sent from other users include a link for direct replies.
   - Users receive notifications for new messages.

3. **Comment Enhancements**
   - Comments are color-coded by user.
   - Users can tag others with '@' to send message notifications.

4. **Profanity Filter**
   - Robust profanity filter implemented for user comments.

5. **Dynamic Navbar**
   - Includes user balance display, unread message indicator, and mobile-friendly dropdown menu.

6. **Custom Logo**
   - Designed logo used in header and favicon.

7. **Sorting and Display Options**
   - Users can sort listings and collapse/expand listing details.

8. **Profile Pictures**
   - Users can upload profile pictures, visible on their profile page, next to comments, and in messages.

9. **User Account Actions**
   - Users can edit profile information, change passwords, and delete accounts.

10. **Reporting System**
    - Users can report users, comments, and listings.

11. **Search Feature**
    - Implemented search functionality for listings.

12. **Transaction History**
    - Users can view past bids and transactions. Dynamic tables for easy viewing.

13. **Dark Mode/Light Mode**
    - Theme support with user preference memory.

14. **Countdown Timer**
    - Live countdown timer on listing pages.

15. **Category Hover Descriptions**
    - Short descriptions appear on category hover.

16. **Celery Beat and Redis Integration**
    - Recurring tasks automate listing expiration, winner declaration, and escrow transfers.

17. **Custom Error Handling**
    - Custom error messages and handling for various scenarios.

18. **Automated Systems**
    - Automated messages for various user actions and system events. (see below for more information)
    - Automated bid removal at 24 hours prior to auction close if bid is unfunded.
    - Automated listing closure and fee processing.
    - Automated transfer of funds to escrow and seller upon auction close.
    - Automated messages to admin for various issues and unexpected events.

19. **User Fee System**
    - Automated fee processing for all auctions
    - 10% fee on all successful auctions
    - Additional 5% fee for early auction closure, bids or no bids. (see below for more details)
    - All fee funds are added to the site account balance.

20. **Maintenance Tasks for Admin**
    - Admin can randomize listing dates for demonstration purposes.
    - Admin can update the closing dates for all listings
    - Admin can use reset_database() to clear all bids, comments, messages, and transactions, while keeping
      users and listings. This function will also give all users $1,000 and set a random listing date for 
      all listings. Perfect for testing and demonstration purposes.


## Usage

### Optional -- Included Test Database
- A test database is included with sample data for testing and demonstration purposes.
- You must update the listing dates or else the auctions will all be closed. 
    - From github repo, be sure to include the db.sqlite3 file in the commerce directory.
    - Inside of commerce/auctions/views.py, uncomment the following lines: 
        - `# from . import maintenance`
        - `# maintenance.reset_database()`
    - Run the server and navigate to or refresh the index page.
    - Comment out the lines again and restart the server.
- Use django admin to view all users, if you want to access a user account the password is lowercase username and email is lowercase username '@email.com'.
- If you want to erase the bids, messages, comments, and transactions, you can use the admin interface to delete all objects of those types.


### Installation and startup
1. Install Django and required dependencies.
2. Clone the project repository.
3. Set up the database and run migrations. (Optional: use the included test database)
4. Run the Django development server.
5. Run Redis server, Celery worker, and Celery beat for recurring tasks.

```bash
pip install -r requirements.txt
git clone https://github.com/MyPetLobster/commerce
cd commerce
python manage.py migrate
python manage.py createsuperuser (or use the included admin account)
python manage.py runserver

**In a new terminal window**
redis-server

**In a new terminal window**
celery -A commerce worker -l info

**In a new terminal window**
celery -A commerce beat -l info
```



## Auction Flow and Messaging

I wrote all this out to help me wrap my head around my own system and test all the automated actions. If you're curious about the inner workings of Yard Sale, read on!

### Placing Bids
- User clicks on the "Place Bid" button on the listing page.
- Form validation ensures the bid is higher than the current bid.
- User submits the form to place bid.
  - If there are less than 24 hours left on listing AND user has insufficient funds to cover the bid, the bid is rejected.
    - Message the bidder: `send_insufficient_funds_notification()`.
  - If the user has insufficient funds, but there are more than 24 hours left, the bid is accepted conditionally.
    - Message the bidder: `send_bid_success_message_low_funds()` -- includes time left to deposit funds.
    - Message the previous high bidder: `message_previous_high_bidder()`.
    - Message the seller: `send_bid_success_message_seller()`.
  - If the user has sufficient funds, the bid is accepted.
    - Message the bidder: `send_bid_success_message_bidder()`.
    - Message the previous high bidder: `message_previous_high_bidder()`.
    - Message the seller: `send_bid_success_message_seller()`.
- Update the listing with the new high bid.

### Closing Auctions

#### Close Auction Early (seller action)
- User clicks on the "Close Auction" button on the listing page.
- If there are less than 24 hours left, the auction cannot be closed early.
- If there are no active bids, the listing is closed immediately.
  - `listing.cancelled` set to True, `listing.active` set to False.
  - Message the seller: `notify_seller_closed_no_bids()`.
  - `helpers.charge_early_closing_fee()` -- 5% fee on listing price.
  - Message the seller: `send_early_closing_fee_message()` -- 5% fee on listing price.
    - If the seller has insufficient funds to cover the 5% fee when no bids are made:
      - Message seller: `send_fee_failure_message()`.
      - The seller has 7 days to deposit funds to cover the fee before additional fees begin to accrue.
      - This is checked by the task `check_user_fees()` which runs every 12 hours.
        - For each day beyond the 7 day grace period, the seller is charged an additional 5% fee on the listing price.
        - On day 28, a message is sent to the seller notifying them of imminent account deactivation and legal action: `send_account_closure_message()`.
        - After 30 days, the seller account is deactivated (password and username changed), and the issue is escalated to legal department/collections.

- If there ARE active bids, 24-hour delay before auction is closed, and bidders have 24 hours after closing to deposit funds into their account and submit to escrow before their bid is removed.
  - `listing.cancelled` set to True.
  - Message the seller and bidders: `notify_all_early_closing()` -- includes new closing date and fee notice for seller.

#### Auction Expiration (automated action)
- `tasks.set_inactive()`, runs every 60 seconds and is the main task for closing auctions.
  - Calls `helpers.declare_winner()`.
  - If `highest_bid.user.balance < highest_bid.amount`, `declare_winner()` returns without assigning a winner.
    - The recurring task `check_if_bids_funded()` runs every 15 minutes and will remove bids for listings 24 hours before closing if the listing was NOT closed early by the seller. If the listing IS closed early, `listing.cancelled` is set to True, and the new cutoff date for depositing sufficient funds is set to 24 hours after the early closing date.
  - `declare_winner()` will send messages to all bidders and the seller: `notify_all_closed_listing()`.
  - `declare_winner()` will initiate transfer to escrow w/ `helpers.transfer_to_escrow()`.
    - If the buyer balance < highest_bid.amount:
      - `a_msg.get_escrow_fail_message()` -- includes time left to deposit funds. Only relevant in cases where auction was not closed early by the seller.
    - Else:
      - `a_msg.get_escrow_success_message()` if escrow transfer succeeds.
  - If no bids, `notify_seller_closed_no_bids()`.

- If the automatic escrow transfer succeeds, the seller will have a button to confirm shipping that will appear on the listing's page.
- If the automatic escrow transfer fails, the winning bidder will have a button to transfer the funds to escrow that will appear on the listing's page. This action, `move_to_escrow()`, simply calls upon `helpers.transfer_to_escrow()` if the winner has sufficient funds.
- Confirm Shipping: When the buyer presses the confirm shipping button, the funds in escrow are transferred to the seller's account, minus the fee, which is transferred to the site account.
  - `helpers.transfer_to_seller()` handles money and transaction object creation.
  - `send_shipping_confirmation_messages()` to the buyer and seller, confirming successful transfer.
  - If escrow is empty when it should not be, admin alerted with message: `send_escrow_empty_alert_message()`.

#### Cancel Bids ####
  - User clicks on the "Cancel Bid" button on the listing page.
  - If the listing expires in less than 24 hours, the bid cannot be canceled.
  - If the canceled bid was the highest bid:
    - Determine new high bidder, send message to notify both parties:
      - `send_bid_cancelled_message_confirmation()`.
      - `send_bid_cancelled_message_new_high_bidder()`.
  - Get message template to seller to notify them of canceled bid depending on if there are more bids:
    - `get_bid_cancelled_message_seller_no_bids`.
    - `get_bid_cancelled_message_seller_bids`.
    - Send message and update listing.
  - The task `check_if_bids_funded()` runs every 15 minutes and will remove bids for listings 24 hours before closing if the listing was NOT closed early by the seller.
    - Message sent to the bidder who has bid removed: `send_bid_removed_message()`.

#### Withdraw Funds ####
  - User clicks on the "Withdraw Funds" button on the user's account page.
  - Users cannot overdraw their account intentionally from the front end.
  - If the user has insufficient funds, the withdrawal is rejected by the form.
  - If the user has active bids on any listings that are less than 24 hours from closing, they must keep a balance that can cover the bids for the expiring auctions.
    - If the withdraw would leave the user with insufficient funds to cover the bids, the withdrawal is rejected: `send_message_deny_withdrawal()`.
  - If the user has active bids on any listings that are closing in less than 72 hours, there are not constraints, but a message is sent to the user to notify of the time left and the amount of funds that should be kept in the account to cover the bids for upcoming closing auctions. The message also tells them which auction they bid on will be the first to close.
    - `send_message_withdrawal_72()`.
  - If no active bids or sufficient funds to cover the bids, the withdrawal is accepted:
    - `send_message_withdrawal_success()`.
    - Update user.balance, record transaction.