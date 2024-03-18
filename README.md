# commerce
CS50w - Project 2 - eBay-like e-commerce auction site







## Actions and System Message Flow

- **Placing Bids**
    - User clicks on the "Place Bid" button on the listing page
    - Form validation to ensure the bid is higher than the current bid
    - User submits the form to place bid
        - If there are less than 24 hours left on listing AND user has insufficient funds to cover the bid, the bid is rejected
            - Message the bidder, send_insufficient_funds_notification()
        - If the user has insufficient funds, but there are more than 24 hours left, the bid is accepted conditionally
            - Message the bidder, send_bid_success_message_low_funds() -- includes time left to deposit funds
            - Message the previous high bidder, message_previous_high_bidder()
            - Message the seller, send_bid_success_message_seller()
        - If the user has sufficient funds, the bid is accepted
            - Message the bidder, send_bid_success_message_bidder()
            - Message the previous high bidder, message_previous_high_bidder()
            - Message the seller, send_bid_success_message_seller()
    - Update the listing with the new high bid

- **Closing Auctions**
    - Close auction early (seller action)
        - User clicks on the "Close Auction" button on the listing page
        - If there are less than 24 hours left, the auction cannot be closed early.
        - If there are no active bids, the listing is closed immediately
            - Message the seller, send_early_closing_fee_message() -- 5% fee on listing price
        - If there ARE active bids, 24 hour delay before auction is closed
            - 

