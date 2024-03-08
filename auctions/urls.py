from django.urls import path

from . import views, actions

urlpatterns = [
    path("", views.index, name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("create", views.create, name="create"),
    path("listing/<int:listing_id>", views.listing, name="listing"),
    path("watchlist", views.watchlist, name="watchlist"),
    path('transactions/<int:user_id>', views.transactions, name='transactions'),
    path('messages/<int:user_id>', views.messages, name='messages'),
    path('categories', views.categories, name="categories"),
    path('category/<int:category_id>', views.category, name="category"),
    path('listings', views.listings, name="listings"),
    path('profile/<int:user_id>', views.profile, name='profile'),
    path('about', views.about, name='about'),
    path('search', views.search, name='search'),
    path("add_to_watchlist/<int:listing_id>", actions.add_to_watchlist, name="add_to_watchlist"),
    path('remove_from_watchlist/<int:listing_id>', actions.remove_from_watchlist, name='remove_from_watchlist'),
    path('close_listing/<int:listing_id>', actions.close_listing, name='close_listing'),
    path('comment/<int:listing_id>', actions.comment, name='comment'),
    path('edit/<int:user_id>', actions.edit, name='edit'),
    path('change_password/<int:user_id>', actions.change_password, name='change_password'),
    path('sort', actions.sort, name='sort'),
    path('deposit/<int:user_id>', actions.deposit, name='deposit'),
    path('withdraw/<int:user_id>', actions.withdraw, name='withdraw'),
    path('confirm_shipping/<int:listing_id>', actions.confirm_shipping, name='confirm_shipping'),
    path('mark_as_read/<int:message_id>', actions.mark_as_read, name='mark_as_read'),
    path('mark_all_as_read/<int:user_id>', actions.mark_all_as_read, name='mark_all_as_read'),
    path('delete_message/<int:message_id>', actions.delete_message, name='delete_message'),
    path('sort_messages', actions.sort_messages, name='sort_messages'),
    path('move_to_escrow/<int:listing_id>', actions.move_to_escrow, name='move_to_escrow'),
]
