from django.urls import path

from . import views, actions

urlpatterns = [
    path("", views.index, name="index"),
    path("about", views.about, name="about"),
    path("add_to_watchlist/<int:listing_id>", actions.add_to_watchlist, name="add_to_watchlist"),
    path("cancel_bid/<int:listing_id>", actions.cancel_bid, name="cancel_bid"),
    path("categories", views.categories, name="categories"),
    path("category/<int:category_id>", views.category, name="category"),
    path("change_password/<int:user_id>", actions.change_password, name="change_password"),
    path("close_listing/<int:listing_id>", actions.close_listing, name="close_listing"),
    path("comment/<int:listing_id>", actions.comment, name="comment"),
    path("confirm_shipping/<int:listing_id>", actions.confirm_shipping, name="confirm_shipping"),
    path("create", views.create, name="create"),
    path("delete_account/<int:user_id>", actions.delete_account, name="delete_account"),
    path("delete_message/<int:message_id>", actions.delete_message, name="delete_message"),
    path("deposit/<int:user_id>", actions.deposit, name="deposit"),
    path("edit/<int:user_id>", actions.edit, name="edit"),
    path("listing/<int:listing_id>", views.listing, name="listing"),
    path("listings", views.listings, name="listings"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("delete_comment/<int:comment_id>", actions.delete_comment, name="delete_comment"),
    path("file_dispute/<int:listing_id>", actions.file_dispute, name="file_dispute"),
    path("mark_all_as_read/<int:user_id>", actions.mark_all_as_read, name="mark_all_as_read"),
    path("mark_all_as_unread/<int:user_id>", actions.mark_all_as_unread, name="mark_all_as_unread"),
    path("mark_as_read/<int:message_id>", actions.mark_as_read, name="mark_as_read"),
    path("messages/<int:user_id>", views.messages, name="messages"),
    path("move_to_escrow/<int:listing_id>", actions.move_to_escrow, name="move_to_escrow"),
    path("profile/<int:user_id>", views.profile, name="profile"),
    path("register", views.register, name="register"),
    path("remove_from_watchlist/<int:listing_id>", actions.remove_from_watchlist, name="remove_from_watchlist"),
    path("remove_inactive_from_watchlist", actions.remove_inactive_from_watchlist, name="remove_inactive_from_watchlist"),
    path("report_comment/<int:comment_id>", actions.report_comment, name="report_comment"),
    path("report_listing/<int:listing_id>", actions.report_listing, name="report_listing"),
    path("report_user/<int:user_id>", actions.report_user, name="report_user"),
    path("search", views.search, name="search"),
    path("sort", actions.sort, name="sort"),
    path("sort_messages", actions.sort_messages, name="sort_messages"),
    path("transactions/<int:user_id>", views.transactions, name="transactions"),
    path("watchlist", views.watchlist, name="watchlist"),
    path("withdraw/<int:user_id>", actions.withdraw, name="withdraw"),
]
