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
            - listing.cancelled set to True, listing.active set to False
            - Message the seller, notify_seller_closed_no_bids()
            - helpers.charge_early_closing_fee() -- 5% fee on listing price
            - Message the seller, send_early_closing_fee_message() -- 5% fee on listing price
                - If the seller has insufficient funds to cover the 5% fee when no bids are made. 
                    - Message seller, send_fee_failure_message()
                    - The seller has 7 days to deposit funds to cover the fee before additional fees begin to accrue
                    - This is checked by the task 'check_user_fees()' which runs every 12 hours.
                        - For each day beyond the 7 day grace period, the seller is charged an additional 5% fee on the listing price
                        - On day 28 a message is sent to the seller notifying them of imminent account deactivation and legal action send_account_closure_message()
                        - After 30 days, the seller account is deactivated (password and username changed) and the issue is escalated to legal department/collections

        - If there ARE active bids, 24 hour delay before auction is closed and bidders have 24 hours after closing to deposit funds into their account and submit to escrow before their bid is removed.
            - listing.cancelled set to True
            - Message the seller and bidders, notify_all_early_closing() -- includes new closing date and fee notice for seller



    - Auction Expiration (automatic)
        - tasks.set_inactive(), runs every 60 seconds and is the main task for closing auctions
            - calls helpers.declare_winner(). 
            - If highest_bid.user.balance < highest_bid.amount, declare_winner() returns without assigning a winner. 
                - The recurring task check_if_bids_funded() runs every 15 minutes and will remove bids for listings 24 hours before closing if the listing was NOT closed early by seller. If the listing IS closed early, listing.cancelled is set to True and the new cutoff date for depositing sufficient funds is set to 24 hours after the early closing date.

            - declare_winner() will send messages to all bidders and seller, notify_all_closed_listing()
            - declare_winner() will initiate transfer to escrow w/ helpers.transfer_to_escrow()
                - if the buyer.balance < highest_bid.amount:
                    - a_msg.get_escrow_fail_message() -- includes time left to deposit funds. Only relevant in cases where auction was not closed early by seller
                - else:
                    - a_msg.get_escrow_success_message() if escrow transfer succeeds 

            - If no bids, notify_seller_closed_no_bids()

        - If the automatic escrow transfer succeeds, the seller will have a button to confirm shipping that will appear on the listing's page. 

        - If the automatic escrow transfer fails, the winning bidder will have a button to transfer the funds to escrow that will appear on the listing's page. This action, move_to_escrow() simply calls upon helpers.transfer_to_escrow() if the winner has sufficient funds. 

        - Confirm Shipping, when the buyer presses the confirm shipping button, the funds in escrow are transferred to the seller's account, minus the fee which is transferred to the site account. 
            - helpers.transfer_to_seller() handles money and transaction object creation


    